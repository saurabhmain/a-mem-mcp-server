"""
MCP Server für A-MEM: Agentic Memory System

Vollständiger MCP Server mit Tools für Memory Management.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from .core.logic import MemoryController
from .models.note import NoteInput

# Server initialisieren
server = Server("a-mem")
controller = MemoryController()

@server.list_tools()
async def list_tools() -> list[Tool]:
    """Listet alle verfügbaren Tools."""
    return [
        Tool(
            name="create_atomic_note",
            description="Speichert eine neue Information im Memory System. Startet automatisch den Linking- und Evolution-Prozess im Hintergrund.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Der Text der Notiz/Erinnerung, die gespeichert werden soll."
                    },
                    "source": {
                        "type": "string",
                        "description": "Quelle der Information (z.B. 'user_input', 'file', 'api').",
                        "default": "user_input"
                    }
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="retrieve_memories",
            description="Sucht nach relevanten Erinnerungen basierend auf semantischer Ähnlichkeit. Gibt die besten Matches mit verknüpften Kontexten zurück.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Die Suchanfrage für die Memory-Suche."
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximale Anzahl der Ergebnisse (Standard: 5).",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_memory_stats",
            description="Gibt Statistiken über das Memory System zurück (Anzahl Nodes, Edges, etc.).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="delete_atomic_note",
            description="Löscht eine Note aus dem Memory System. Entfernt die Note aus Graph und Vector Store sowie alle zugehörigen Verbindungen.",
            inputSchema={
                "type": "object",
                "properties": {
                    "note_id": {
                        "type": "string",
                        "description": "Die UUID der Note, die gelöscht werden soll."
                    }
                },
                "required": ["note_id"]
            }
        ),
        Tool(
            name="add_file",
            description="Speichert den Inhalt einer Datei (z.B. .md) als Note im Memory System. Unterstützt automatisches Chunking für große Dateien (>16KB).",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Pfad zur Datei, die gespeichert werden soll (relativ oder absolut)."
                    },
                    "file_content": {
                        "type": "string",
                        "description": "Alternativ: Direkter Dateiinhalt als String (wenn file_path nicht angegeben)."
                    },
                    "chunk_size": {
                        "type": "integer",
                        "description": "Maximale Größe pro Chunk in Bytes (Standard: 15000, um unter 16KB Limit zu bleiben).",
                        "default": 15000,
                        "minimum": 1000,
                        "maximum": 16384
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="reset_memory",
            description="Setzt das komplette Memory System zurück (Graph + Vector Store). Löscht alle Notes, Edges und Embeddings. ACHTUNG: Diese Aktion kann nicht rückgängig gemacht werden!",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Führt ein Tool aus."""
    
    if name == "create_atomic_note":
        content = arguments.get("content", "")
        source = arguments.get("source", "user_input")
        
        if not content:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "content is required"}, indent=2)
            )]
        
        try:
            note_input = NoteInput(content=content, source=source)
            note_id = await controller.create_note(note_input)
            
            result = {
                "status": "success",
                "note_id": note_id,
                "message": f"Note created with ID: {note_id}. Evolution started in background."
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    elif name == "retrieve_memories":
        query = arguments.get("query", "")
        max_results = arguments.get("max_results", 5)
        
        if not query:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "query is required"}, indent=2)
            )]
        
        try:
            results = await controller.retrieve(query)
            
            # Limit results
            results = results[:max_results]
            
            output = []
            for res in results:
                context_str = ", ".join([f"[{rn.id}] {rn.contextual_summary}" for rn in res.related_notes])
                output.append({
                    "id": res.note.id,
                    "content": res.note.content,
                    "summary": res.note.contextual_summary,
                    "keywords": res.note.keywords,
                    "tags": res.note.tags,
                    "relevance_score": float(res.score),
                    "connected_memories": len(res.related_notes),
                    "connected_context": context_str
                })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "success",
                    "query": query,
                    "results_count": len(output),
                    "results": output
                }, indent=2, ensure_ascii=False)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    elif name == "get_memory_stats":
        try:
            graph = controller.storage.graph.graph
            stats = {
                "status": "success",
                "graph_nodes": graph.number_of_nodes(),
                "graph_edges": graph.number_of_edges(),
                "memory_count": graph.number_of_nodes(),
                "connection_count": graph.number_of_edges()
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(stats, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    elif name == "delete_atomic_note":
        note_id = arguments.get("note_id", "")
        
        if not note_id:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "note_id is required"}, indent=2)
            )]
        
        try:
            success = await controller.delete_note(note_id)
            
            if success:
                result = {
                    "status": "success",
                    "note_id": note_id,
                    "message": f"Note {note_id} deleted successfully. All connections removed."
                }
            else:
                result = {
                    "status": "error",
                    "note_id": note_id,
                    "message": f"Note {note_id} not found or could not be deleted."
                }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    elif name == "add_file":
        file_path = arguments.get("file_path", "")
        file_content = arguments.get("file_content", "")
        chunk_size = arguments.get("chunk_size", 15000)
        
        # Prüfe ob file_path oder file_content angegeben
        if not file_path and not file_content:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "Either file_path or file_content is required"}, indent=2)
            )]
        
        try:
            # Lese Datei falls file_path angegeben
            if file_path:
                path = Path(file_path)
                if not path.exists():
                    return [TextContent(
                        type="text",
                        text=json.dumps({"error": f"File not found: {file_path}"}, indent=2)
                    )]
                
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    source = f"file:{path.name}"
                except UnicodeDecodeError:
                    # Fallback für Binärdateien
                    with open(path, 'rb') as f:
                        content_bytes = f.read()
                    file_content = content_bytes.decode('utf-8', errors='replace')
                    source = f"file:{path.name}"
            else:
                source = "file:direct_content"
            
            # Prüfe Größe und chunk wenn nötig
            content_bytes = file_content.encode('utf-8')
            file_size = len(content_bytes)
            
            if file_size <= chunk_size:
                # Datei passt in eine Note
                note_input = NoteInput(content=file_content, source=source)
                note_id = await controller.create_note(note_input)
                
                result = {
                    "status": "success",
                    "note_id": note_id,
                    "file_size": file_size,
                    "chunks": 1,
                    "message": f"File stored as single note with ID: {note_id}. Evolution started in background."
                }
            else:
                # Chunking erforderlich
                chunks = []
                chunk_count = (file_size + chunk_size - 1) // chunk_size
                
                for i in range(chunk_count):
                    start = i * chunk_size
                    end = min(start + chunk_size, file_size)
                    chunk_content = content_bytes[start:end].decode('utf-8', errors='replace')
                    
                    # Füge Chunk-Info hinzu
                    chunk_header = f"[Chunk {i+1}/{chunk_count} from {source}]\n\n"
                    chunk_note_content = chunk_header + chunk_content
                    
                    note_input = NoteInput(
                        content=chunk_note_content,
                        source=f"{source}:chunk_{i+1}"
                    )
                    note_id = await controller.create_note(note_input)
                    chunks.append(note_id)
                
                result = {
                    "status": "success",
                    "file_size": file_size,
                    "chunks": chunk_count,
                    "note_ids": chunks,
                    "message": f"File split into {chunk_count} chunks. All notes created. Evolution started in background."
                }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    elif name == "reset_memory":
        try:
            success = await controller.reset_memory()
            
            if success:
                result = {
                    "status": "success",
                    "message": "Memory system reset successfully. All notes, edges, and embeddings have been deleted."
                }
            else:
                result = {
                    "status": "error",
                    "message": "Failed to reset memory system. Check logs for details."
                }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]
    
    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"}, indent=2)
        )]

async def main():
    """Hauptfunktion für den MCP Server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
