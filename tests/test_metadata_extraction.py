#!/usr/bin/env python3
"""
Test script to debug metadata extraction for dacoity cases.
"""
import os
import sys
sys.path.append('src/bg_creation')

from extract_metadata import MetadataExtractor
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

def test_metadata_extraction():
    """Test metadata extraction on a dacoity case."""
    
    # Sample dacoity case text (simulated)
    sample_dacoity_text = """
    IN THE HIGH COURT OF BOMBAY AT AURANGABAD
    
    CRIMINAL APPEAL NO. 123 OF 2020
    
    Abdulla Momin ... Appellant
    Versus
    State of Maharashtra ... Respondent
    
    Coram: Hon'ble Mr. Justice XYZ
    
    Heard on: 15th January, 2021
    Decided on: 20th January, 2021
    
    For Appellant: Adv. ABC
    For Respondent: APP Shri DEF
    
    JUDGMENT:
    
    This criminal appeal challenges the conviction and sentence passed by the Sessions Court 
    under Sections 395 and 397 of the Indian Penal Code (IPC) for the offense of dacoity.
    
    The prosecution case is that the appellant along with four other accused persons committed 
    dacoity at the house of complainant. They were armed with deadly weapons and caused 
    grievous hurt to the victims while committing robbery.
    
    The trial court found that five or more persons were involved in committing dacoity as 
    defined under Section 395 IPC. The court also found that during the commission of dacoity, 
    the accused attempted to cause death or grievous hurt to the victims, thereby attracting 
    Section 397 IPC.
    
    The accused was convicted under IPC 395 and IPC 397 and sentenced to rigorous imprisonment 
    for 7 years and fine of Rs. 5000.
    """
    
    # Initialize extractor
    extractor = MetadataExtractor()
    
    # Extract metadata
    print("Testing metadata extraction...")
    metadata = extractor.extract_metadata(sample_dacoity_text)
    
    print("\nExtracted metadata:")
    print(f"Case Number: {metadata.case_number}")
    print(f"Case Title: {metadata.case_title}")
    print(f"Court Name: {metadata.court_name}")
    print(f"Sections Invoked: {metadata.sections_invoked}")
    print(f"Most Appropriate Section: {metadata.most_appropriate_section}")
    print(f"Appellant: {metadata.appellant_or_petitioner}")
    print(f"Respondent: {metadata.respondent}")
    
    # Check if we got the most appropriate section
    if metadata.most_appropriate_section:
        print(f"\n✓ Successfully identified most appropriate section: {metadata.most_appropriate_section}")
    else:
        print(f"\n✗ Failed to identify most appropriate section")
    
    return metadata

if __name__ == "__main__":
    test_metadata_extraction()