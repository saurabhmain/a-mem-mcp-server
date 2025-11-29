"""Test Unstructured import."""

try:
    from unstructured.partition.pdf import partition_pdf
    print("✅ Import successful")
    print(f"   Function: {partition_pdf}")
except ImportError as e:
    print(f"❌ ImportError: {e}")
except Exception as e:
    print(f"❌ Error ({type(e).__name__}): {e}")
    import traceback
    traceback.print_exc()

