"""
Test script to demonstrate the difference between old token-based chunking
and new RecursiveDocumentSplitter paragraph-based chunking.
"""

from src.services.chunking_service import ChunkingService
import logging

logging.basicConfig(level=logging.INFO)

# Sample legal text with clear paragraph structure
legal_text = """SUPREME COURT OF INDIA

CRIMINAL APPEAL NO. 456 OF 2024

Between:
State of Punjab ...Appellant
Versus
Accused Person ...Respondent

JUDGMENT

1. This appeal arises from the judgment of the High Court dated March 15, 2024, where the respondent was acquitted of charges under Sections 302, 307, and 201 of the Indian Penal Code. The prosecution challenged this acquittal on multiple grounds.

2. FACTS OF THE CASE: The prosecution case is that on the night of January 10, 2023, the deceased Ramesh Kumar was found dead at his residence in Model Town, Chandigarh. The circumstances surrounding the death pointed towards homicide rather than suicide or accidental death.

3. BACKGROUND AND MOTIVE: The accused and the deceased had a long-standing property dispute dating back to 2015. Several witnesses, including neighbors and family members, testified about heated arguments between them regarding the division of ancestral property worth approximately Rs. 5 crores.

4. PROSECUTION EVIDENCE: The medical evidence showed multiple injuries on the deceased's body, including contusions on the neck, abrasions on the arms, and defensive wounds on the palms. The post-mortem report prepared by Dr. Suresh Sharma indicated death due to manual strangulation, with the time of death estimated between 10 PM and midnight.

5. WITNESS TESTIMONIES: The prosecution examined 15 witnesses. PW-1, the wife of the deceased, stated that she heard sounds of struggle from the bedroom. PW-2 and PW-3, neighbors, testified seeing the accused leaving the premises around 11:30 PM on the night of the incident.

6. FORENSIC EVIDENCE: The forensic team recovered fingerprints matching the accused from the crime scene. DNA analysis of materials found under the deceased's fingernails showed a match with the accused's DNA profile with 99.9% probability.

7. DEFENCE CASE: The accused claimed alibi, stating he was at a wedding ceremony 50 kilometers away from the crime scene. He produced three witnesses to support his claim. However, the trial court found discrepancies in their statements during cross-examination.

8. HIGH COURT REASONING: The High Court acquitted the accused primarily on the ground that the prosecution failed to establish the exact time when the accused allegedly committed the crime. The court observed that the testimonies of neighbors were contradictory regarding the timing.

9. LEGAL PRINCIPLES: In appeals against acquittal, the Supreme Court has consistently held that the appellate court should not interfere unless the findings are perverse, illegal, or suffer from non-consideration of material evidence. The case of Chandrappa v. State of Karnataka (2007) 4 SCC 415 provides the guiding principles.

10. OUR ANALYSIS: After careful consideration of the evidence, including the medical reports, forensic analysis, and witness testimonies, we find that the High Court erred in appreciating the cumulative effect of circumstantial evidence. Each piece of evidence, when considered in isolation, may appear weak, but when viewed collectively, they form an unbroken chain pointing towards the guilt of the accused.

11. CONCLUSION: We find that the prosecution has established the case beyond reasonable doubt. The judgment of the High Court is set aside, and the conviction under Section 302 IPC is restored. The accused is sentenced to life imprisonment. The appeal is allowed."""

print("=" * 80)
print("TESTING HAYSTACK RECURSIVE DOCUMENT SPLITTER")
print("=" * 80)

# Test with default chunk size (512 tokens)
print("\n1. Default chunk size (512 tokens):")
cs_default = ChunkingService()
chunks_default = cs_default.chunk_text(legal_text)
print(f"   Total chunks: {len(chunks_default)}")
print(f"   Average tokens per chunk: {sum(c.token_count for c in chunks_default) / len(chunks_default):.1f}")

for i, chunk in enumerate(chunks_default):
    print(f"\n   Chunk {i} ({chunk.token_count} tokens):")
    print(f"   First 150 chars: {chunk.text[:150]}...")
    print(f"   Last 100 chars: ...{chunk.text[-100:]}")

# Test with smaller chunk size to show multiple chunks
print("\n" + "=" * 80)
print("\n2. Smaller chunk size (100 tokens) - Shows paragraph-based splitting:")
cs_small = ChunkingService(chunk_size=100, overlap=20)
chunks_small = cs_small.chunk_text(legal_text)
print(f"   Total chunks: {len(chunks_small)}")
print(f"   Average tokens per chunk: {sum(c.token_count for c in chunks_small) / len(chunks_small):.1f}")

for i, chunk in enumerate(chunks_small[:5]):  # Show first 5 chunks
    print(f"\n   Chunk {i} ({chunk.token_count} tokens):")
    print(f"   First 200 chars: {chunk.text[:200]}...")

print("\n" + "=" * 80)
print("BENEFITS OF RECURSIVE SPLITTING:")
print("=" * 80)
print("1. Splits at natural boundaries (paragraphs first, then sentences)")
print("2. Preserves legal document structure (numbered points stay together)")
print("3. Better semantic coherence within each chunk")
print("4. Overlap ensures important context isn't lost between chunks")
print("=" * 80)
