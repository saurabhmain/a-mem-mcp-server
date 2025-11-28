"""Check graph save logs."""

from pathlib import Path
import json

log_file = Path("data/graph_save.log")
graph_file = Path("data/graph/knowledge_graph.json")

print("="*60)
print("📋 Graph Save Logs Check")
print("="*60 + "\n")

if log_file.exists():
    print(f"✅ Log file exists: {log_file}")
    print(f"   Size: {log_file.stat().st_size} bytes\n")
    print("Last 30 lines:")
    print("-"*60)
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines[-30:]:
            print(line.rstrip())
else:
    print(f"❌ Log file does not exist: {log_file}")
    print("   This means save_snapshot() hasn't been called yet with the new logging.\n")

print("\n" + "="*60)
print("📊 Graph File Status")
print("="*60 + "\n")

if graph_file.exists():
    with open(graph_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    nodes = len(data.get("nodes", []))
    links = len(data.get("links", []))
    size = graph_file.stat().st_size
    
    print(f"File: {graph_file}")
    print(f"Size: {size} bytes")
    print(f"Nodes: {nodes}")
    print(f"Links: {links}")
    
    if nodes == 0:
        print("\n⚠️  Graph file is empty!")
    else:
        print("\n✅ Graph file has data!")
else:
    print(f"❌ Graph file does not exist: {graph_file}")

