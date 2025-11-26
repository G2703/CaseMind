"""
Script to remove tier_4_procedural from all template JSON files.
This optimizes the fact extraction process by removing metadata fields that
are already captured in Phase 1 summarization.
"""

import json
from pathlib import Path

def remove_tier4_from_template(template_path: Path) -> bool:
    """
    Remove tier_4_procedural section from a template file.
    
    Args:
        template_path: Path to template JSON file
        
    Returns:
        True if modified, False otherwise
    """
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        
        # Navigate to schema properties
        if 'json_schema' not in template:
            print(f"  Skipping {template_path.name} - no json_schema")
            return False
        
        schema = template.get('json_schema', {}).get('schema', {})
        properties = schema.get('properties', {})
        
        # Check if tier_4_procedural exists
        if 'tier_4_procedural' not in properties:
            print(f"  Skipping {template_path.name} - no tier_4_procedural")
            return False
        
        # Remove tier_4_procedural
        del properties['tier_4_procedural']
        print(f"  ✓ Removed tier_4_procedural from {template_path.name}")
        
        # Update required array
        required = schema.get('required', [])
        if 'tier_4_procedural' in required:
            required.remove('tier_4_procedural')
            schema['required'] = required
            print(f"    - Removed from required array")
        
        # Write back to file
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error processing {template_path.name}: {e}")
        return False


def main():
    """Process all template files in templates directory."""
    templates_dir = Path(__file__).parent / "templates"
    
    if not templates_dir.exists():
        print(f"Error: Templates directory not found: {templates_dir}")
        return
    
    print("=" * 80)
    print("REMOVING TIER 4 (PROCEDURAL FACTS) FROM ALL TEMPLATES")
    print("=" * 80)
    print()
    print("Rationale:")
    print("- Tier 4 contains metadata (case_number, court_name, parties, etc.)")
    print("- This is already extracted in Phase 1 (case summarization)")
    print("- Phase 2 only receives case_facts + evidence (no metadata)")
    print("- LLM cannot fill Tier 4 → results in empty fields")
    print("- Solution: Remove Tier 4, use metadata_embedding for procedural info")
    print()
    print("=" * 80)
    print()
    
    # Get all JSON files except templates.json
    template_files = [f for f in templates_dir.glob("*.json") if f.name != "templates.json"]
    
    print(f"Found {len(template_files)} template files to process\n")
    
    modified_count = 0
    skipped_count = 0
    
    for template_file in sorted(template_files):
        result = remove_tier4_from_template(template_file)
        if result:
            modified_count += 1
        else:
            skipped_count += 1
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total templates: {len(template_files)}")
    print(f"Modified: {modified_count}")
    print(f"Skipped: {skipped_count}")
    print()
    print("✓ All templates updated successfully!")
    print()
    print("Next step: Run the ingestion pipeline to test")
    print("  python test_optimized_pipeline.py")


if __name__ == "__main__":
    main()
