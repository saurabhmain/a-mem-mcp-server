#!/usr/bin/env python3
"""
Ollama Model Benchmark Tool
Modern TUI für Geschwindigkeits-Tests von Ollama-Modellen
"""

import asyncio
import time
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

import requests
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, DataTable, ProgressBar, Static, 
    Button, Input, Select, Label, Log, Collapsible
)
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.reactive import reactive
from textual import work
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Ollama API Base URL
OLLAMA_BASE_URL = "http://localhost:11434"

@dataclass
class BenchmarkResult:
    """Speichert Benchmark-Ergebnisse für ein Modell"""
    model: str
    prompt: str
    total_time: float
    tokens_generated: int
    tokens_per_second: float
    first_token_time: float
    avg_token_time: float
    timestamp: str

class OllamaBenchmark:
    """Ollama API Wrapper für Benchmarking"""
    
    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
    
    def list_models(self) -> List[str]:
        """Listet alle verfügbaren Ollama-Modelle"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [model["name"] for model in models]
        except Exception as e:
            print(f"Error listing models: {e}")
            return []
    
    def benchmark_model(
        self, 
        model: str, 
        prompt: str = "Write a short story about a robot learning to paint.",
        max_tokens: int = 100
    ) -> Optional[BenchmarkResult]:
        """Benchmarkt ein Modell und gibt Metriken zurück"""
        try:
            start_time = time.time()
            first_token_time = None
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "num_predict": max_tokens
                    }
                },
                stream=True,
                timeout=300
            )
            response.raise_for_status()
            
            tokens_generated = 0
            full_response = ""
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        
                        # Erste Token-Zeit messen
                        if first_token_time is None and data.get("response"):
                            first_token_time = time.time() - start_time
                        
                        if data.get("response"):
                            tokens_generated += 1
                            full_response += data["response"]
                        
                        # Beende wenn fertig
                        if data.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            total_time = time.time() - start_time
            
            if tokens_generated == 0:
                return None
            
            tokens_per_second = tokens_generated / total_time if total_time > 0 else 0
            avg_token_time = total_time / tokens_generated if tokens_generated > 0 else 0
            
            return BenchmarkResult(
                model=model,
                prompt=prompt,
                total_time=total_time,
                tokens_generated=tokens_generated,
                tokens_per_second=tokens_per_second,
                first_token_time=first_token_time or 0,
                avg_token_time=avg_token_time,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            print(f"Error benchmarking {model}: {e}")
            return None

class BenchmarkApp(App):
    """Haupt-TUI App für Ollama Benchmarking"""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #results-container {
        height: 1fr;
        border: solid $primary;
    }
    
    #model-select {
        width: 1fr;
    }
    
    #prompt-input {
        width: 1fr;
    }
    
    .benchmark-button {
        width: 1fr;
    }
    
    DataTable {
        height: 1fr;
    }
    
    ProgressBar {
        height: 1;
    }
    
    .status-label {
        text-style: bold;
        color: $accent;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "run_benchmark", "Run Benchmark"),
        ("c", "clear_results", "Clear Results"),
        ("s", "save_results", "Save Results"),
    ]
    
    current_model = reactive("")
    current_prompt = reactive("Write a short story about a robot learning to paint.")
    benchmark_running = reactive(False)
    results: List[BenchmarkResult] = reactive([])
    
    def compose(self) -> ComposeResult:
        """Erstellt die UI-Struktur"""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            with Vertical(id="controls"):
                yield Label("🎯 Ollama Model Benchmark Tool", classes="status-label")
                
                with Horizontal():
                    yield Label("Model:", classes="label")
                    yield Select(id="model-select", options=[], prompt="Select Model...")
                
                with Horizontal():
                    yield Label("Prompt:", classes="label")
                    yield Input(
                        id="prompt-input",
                        value=self.current_prompt,
                        placeholder="Enter test prompt..."
                    )
                
                with Horizontal():
                    yield Button("🚀 Run Benchmark", id="run-btn", variant="primary")
                    yield Button("🗑️ Clear Results", id="clear-btn", variant="default")
                    yield Button("💾 Save Results", id="save-btn", variant="default")
                
                yield ProgressBar(id="progress", show_eta=False, total=100)
                yield Label("Ready. Select a model and press 'Run Benchmark'", id="status")
            
            with ScrollableContainer(id="results-container"):
                yield DataTable(id="results-table")
                yield Log(id="log", max_lines=50)
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Wird beim Start aufgerufen"""
        self.load_models()
        self.setup_table()
    
    def load_models(self) -> None:
        """Lädt verfügbare Modelle"""
        benchmark = OllamaBenchmark()
        models = benchmark.list_models()
        
        select = self.query_one("#model-select", Select)
        select.set_options([(model, model) for model in models])
        
        if models:
            self.notify(f"Loaded {len(models)} models", severity="information")
        else:
            self.notify("No models found. Make sure Ollama is running.", severity="warning")
    
    def setup_table(self) -> None:
        """Initialisiert die Results-Tabelle"""
        table = self.query_one("#results-table", DataTable)
        table.add_columns(
            "Model",
            "Tokens/sec",
            "Total Time (s)",
            "Tokens",
            "First Token (s)",
            "Avg Token (ms)",
            "Timestamp"
        )
        table.cursor_type = "row"
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Wird aufgerufen wenn ein Modell ausgewählt wird"""
        if event.control.id == "model-select":
            self.current_model = event.value or ""
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Wird aufgerufen wenn der Prompt geändert wird"""
        if event.control.id == "prompt-input":
            self.current_prompt = event.value
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Behandelt Button-Klicks"""
        if event.button.id == "run-btn":
            self.run_benchmark()
        elif event.button.id == "clear-btn":
            self.clear_results()
        elif event.button.id == "save-btn":
            self.save_results()
    
    def action_run_benchmark(self) -> None:
        """Startet Benchmark (via Binding)"""
        self.run_benchmark()
    
    def action_clear_results(self) -> None:
        """Löscht Results (via Binding)"""
        self.clear_results()
    
    def action_save_results(self) -> None:
        """Speichert Results (via Binding)"""
        self.save_results()
    
    @work(exclusive=True)
    async def run_benchmark(self) -> None:
        """Führt Benchmark aus"""
        if not self.current_model:
            self.notify("Please select a model first", severity="warning")
            return
        
        if self.benchmark_running:
            self.notify("Benchmark already running", severity="warning")
            return
        
        self.benchmark_running = True
        progress = self.query_one("#progress", ProgressBar)
        status = self.query_one("#status", Label)
        log = self.query_one("#log", Log)
        
        # UI Updates
        self.query_one("#run-btn", Button).disabled = True
        progress.update(progress=0)
        status.update(f"🔄 Benchmarking {self.current_model}...")
        log.write(f"[{datetime.now().strftime('%H:%M:%S')}] Starting benchmark for {self.current_model}")
        
        # Benchmark ausführen (in Thread)
        benchmark = OllamaBenchmark()
        
        # Progress Simulation
        async def update_progress():
            for i in range(0, 90, 10):
                await asyncio.sleep(0.1)
                progress.update(progress=i)
        
        progress_task = asyncio.create_task(update_progress())
        
        # Benchmark in Executor (blocking)
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            benchmark.benchmark_model,
            self.current_model,
            self.current_prompt,
            100  # max_tokens
        )
        
        progress_task.cancel()
        progress.update(progress=100)
        
        if result:
            self.results.append(result)
            self.update_table(result)
            
            status.update(
                f"✅ {result.model}: {result.tokens_per_second:.2f} tokens/sec "
                f"({result.tokens_generated} tokens in {result.total_time:.2f}s)"
            )
            log.write(
                f"[{datetime.now().strftime('%H:%M:%S')}] ✅ {result.model}: "
                f"{result.tokens_per_second:.2f} tokens/sec, "
                f"{result.total_time:.2f}s total, "
                f"{result.tokens_generated} tokens"
            )
            self.notify(f"Benchmark completed: {result.tokens_per_second:.2f} tokens/sec", severity="success")
        else:
            status.update(f"❌ Benchmark failed for {self.current_model}")
            log.write(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Benchmark failed")
            self.notify("Benchmark failed. Check logs.", severity="error")
        
        self.query_one("#run-btn", Button).disabled = False
        self.benchmark_running = False
        progress.update(progress=0)
    
    def update_table(self, result: BenchmarkResult) -> None:
        """Aktualisiert die Results-Tabelle"""
        table = self.query_one("#results-table", DataTable)
        table.add_row(
            result.model,
            f"{result.tokens_per_second:.2f}",
            f"{result.total_time:.2f}",
            str(result.tokens_generated),
            f"{result.first_token_time:.3f}",
            f"{result.avg_token_time * 1000:.2f}",
            datetime.fromisoformat(result.timestamp).strftime("%H:%M:%S")
        )
    
    def clear_results(self) -> None:
        """Löscht alle Results"""
        table = self.query_one("#results-table", DataTable)
        table.clear()
        self.results.clear()
        self.query_one("#status", Label).update("Results cleared")
        self.query_one("#log", Log).clear()
        self.notify("Results cleared", severity="information")
    
    def save_results(self) -> None:
        """Speichert Results als JSON"""
        if not self.results:
            self.notify("No results to save", severity="warning")
            return
        
        filename = f"ollama_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(result) for result in self.results],
                    f,
                    indent=2,
                    ensure_ascii=False
                )
            self.notify(f"Results saved to {filename}", severity="success")
            self.query_one("#log", Log).write(f"💾 Saved results to {filename}")
        except Exception as e:
            self.notify(f"Error saving results: {e}", severity="error")

if __name__ == "__main__":
    app = BenchmarkApp()
    app.run()

