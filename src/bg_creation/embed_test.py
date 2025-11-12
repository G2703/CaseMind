from sentence_transformers import SentenceTransformer

# 1. Load a pretrained Sentence Transformer model
model = SentenceTransformer("all-MiniLM-L6-v2")

# The sentences to encode
sentences = [
    "The weather is lovely today.",
    "It's so sunny outside!",
    "He drove to the stadium.",
]

# 2. Calculate embeddings by calling model.encode()
embeddings = model.encode(sentences)
print(embeddings.shape)
# [3, 384]

test = ["The weather is lovely today."]
test_embedding = model.encode(test)
print(test_embedding.shape)
# (1, 384)

# 3. Calculate the embedding similarities
similarities = model.similarity(embeddings, test_embedding)
print(similarities)
# tensor([[1.0000],
#         [0.6660],
#         [0.1046]])