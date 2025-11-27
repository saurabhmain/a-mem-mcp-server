# Ollama Model Benchmark Tool

Modernes TUI (Text User Interface) für Geschwindigkeits-Tests von Ollama-Modellen.

## 🚀 Features

- ✅ **Moderne TUI** mit Textual Framework
- ✅ **Live Metriken**: Tokens/sec, Latency, First Token Time
- ✅ **Multi-Model Testing**: Teste verschiedene Modelle nacheinander
- ✅ **Results Export**: Speichere Ergebnisse als JSON
- ✅ **Real-time Progress**: Live Progress Bar während Benchmark
- ✅ **Interactive Logs**: Detaillierte Logs für jeden Test

## 📋 Installation

```bash
# Installiere Dependencies
pip install textual requests

# Oder nutze requirements.txt
pip install -r requirements.txt
```

## 🎯 Verwendung

```bash
# Starte das Benchmark Tool
python ollama_benchmark.py
```

### TUI Navigation

- **Model auswählen**: Dropdown-Menü oben
- **Prompt anpassen**: Text-Input für Test-Prompt
- **Benchmark starten**: 
  - Button "🚀 Run Benchmark" klicken
  - Oder Taste `r` drücken
- **Results löschen**: 
  - Button "🗑️ Clear Results" klicken
  - Oder Taste `c` drücken
- **Results speichern**: 
  - Button "💾 Save Results" klicken
  - Oder Taste `s` drücken
- **Beenden**: Taste `q` drücken

## 📊 Metriken

Das Tool misst folgende Performance-Metriken:

- **Tokens/sec**: Generierungsgeschwindigkeit
- **Total Time**: Gesamte Antwortzeit
- **Tokens**: Anzahl generierter Tokens
- **First Token Time**: Zeit bis zum ersten Token (TTFT)
- **Avg Token Time**: Durchschnittliche Zeit pro Token

## 💾 Export

Results werden als JSON gespeichert:

```json
[
  {
    "model": "qwen3:4b",
    "prompt": "Write a short story...",
    "total_time": 12.34,
    "tokens_generated": 87,
    "tokens_per_second": 7.05,
    "first_token_time": 0.234,
    "avg_token_time": 0.142,
    "timestamp": "2025-11-27T04:00:00"
  }
]
```

## 🎨 Screenshots

Das TUI zeigt:
- Model-Selektor
- Prompt-Editor
- Live Progress Bar
- Results-Tabelle mit allen Metriken
- Detaillierte Logs

## 🔧 Anpassungen

### Custom Prompts

Du kannst den Standard-Prompt im Code ändern:

```python
current_prompt = reactive("Dein Custom Prompt hier...")
```

### Max Tokens

Standard: 100 Tokens. Ändere in `run_benchmark()`:

```python
result = await loop.run_in_executor(
    None,
    benchmark.benchmark_model,
    self.current_model,
    self.current_prompt,
    200  # max_tokens anpassen
)
```

## 🐛 Troubleshooting

**"No models found"**
- Stelle sicher, dass Ollama läuft: `ollama serve`
- Prüfe, ob Modelle installiert sind: `ollama list`

**"Connection refused"**
- Prüfe Ollama URL (Standard: `http://localhost:11434`)
- Ändere `OLLAMA_BASE_URL` im Code falls nötig

**Benchmark hängt**
- Prüfe Ollama Logs
- Stelle sicher, dass genug RAM/VRAM verfügbar ist

## 📝 Beispiel-Output

```
Model          | Tokens/sec | Total Time | Tokens | First Token | Avg Token
qwen3:4b       | 7.05       | 12.34      | 87     | 0.234       | 142.00
llama3.2:3b    | 12.45      | 8.03       | 100    | 0.189       | 80.30
mistral:7b     | 5.23       | 19.12      | 100    | 0.456       | 191.20
```

## 🎯 Best Practices

1. **Warm-up**: Erste Anfrage kann langsamer sein (Model Loading)
2. **Konsistenz**: Nutze denselben Prompt für faire Vergleiche
3. **Mehrere Runs**: Führe mehrere Benchmarks aus für Durchschnittswerte
4. **System Load**: Schließe andere GPU-intensive Apps während Tests

## 📚 Technische Details

- **Framework**: Textual (moderne Python TUI Library)
- **API**: Ollama REST API (`/api/generate`)
- **Streaming**: Nutzt Streaming für präzise Token-Messung
- **Async**: Asynchrone Ausführung für responsive UI

## 🔗 Links

- [Textual Documentation](https://textual.textualize.io/)
- [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama Models](https://ollama.com/library)



