# A-MEM System Reset Script
# Löscht alle gespeicherten Daten (ChromaDB, Graph, Lock-Files)
#
# ⚠️  WICHTIG: Nach dem Reset muss der MCP Server neu gestartet werden!
# Der Graph wird beim Server-Start geladen und bleibt im Memory.
# Nur ein Neustart des Servers sorgt für einen wirklich leeren Graph.

Write-Host "🔄 Setze A-MEM System komplett zurück..." -ForegroundColor Yellow
Write-Host ""

# ChromaDB löschen
if (Test-Path "data\chroma") {
    Remove-Item -Recurse -Force "data\chroma"
    Write-Host "  ✅ ChromaDB gelöscht" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  ChromaDB existiert nicht" -ForegroundColor Gray
}

# Graph löschen
if (Test-Path "data\graph\knowledge_graph.json") {
    Remove-Item -Force "data\graph\knowledge_graph.json"
    Write-Host "  ✅ Graph gelöscht" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Graph existiert nicht" -ForegroundColor Gray
}

# Lock-File löschen
if (Test-Path "data\graph\graph.lock") {
    Remove-Item -Force "data\graph\graph.lock"
    Write-Host "  ✅ Lock-File gelöscht" -ForegroundColor Green
} else {
    Write-Host "  ⚠️  Lock-File existiert nicht" -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ Dateien gelöscht" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  WICHTIGER HINWEIS:" -ForegroundColor Yellow
Write-Host "   Der MCP Server muss NEU GESTARTET werden!" -ForegroundColor Yellow
Write-Host "   Der Graph wird beim Server-Start geladen und bleibt im Memory." -ForegroundColor Yellow
Write-Host "   Nur ein Neustart des Servers sorgt für einen wirklich leeren Graph." -ForegroundColor Yellow
Write-Host ""
Write-Host "   In Cursor: MCP Server neu laden (Cursor Settings → MCP → Restart)" -ForegroundColor Cyan
Write-Host ""
Write-Host "📊 Verifikation:" -ForegroundColor Cyan

if (Test-Path "data\chroma") {
    Write-Host "  ❌ ChromaDB existiert noch" -ForegroundColor Red
} else {
    Write-Host "  ✅ ChromaDB gelöscht" -ForegroundColor Green
}

if (Test-Path "data\graph\knowledge_graph.json") {
    Write-Host "  ❌ Graph existiert noch" -ForegroundColor Red
} else {
    Write-Host "  ✅ Graph gelöscht" -ForegroundColor Green
}

if (Test-Path "data\graph\graph.lock") {
    Write-Host "  ❌ Lock-File existiert noch" -ForegroundColor Red
} else {
    Write-Host "  ✅ Lock-File gelöscht" -ForegroundColor Green
}

