from openai import OpenAI
import math
import ollama
from itertools import permutations
import numpy as np
from scipy.optimize import linear_sum_assignment

EMBEDDING_MODEL = 'hf.co/CompendiumLabs/bge-base-en-v1.5-gguf'

def add_chunk_to_database(chunk, vector_db):
  embedding = ollama.embed(model=EMBEDDING_MODEL, input=chunk)['embeddings'][0]
  vector_db.append((chunk, embedding))
  return vector_db

def cosine_similarity(a, b):
  dot_product = sum([x * y for x, y in zip(a, b)])
  norm_a = sum([x ** 2 for x in a]) ** 0.5
  norm_b = sum([x ** 2 for x in b]) ** 0.5
  return dot_product / (norm_a * norm_b)

# Calculate best match of single query vector against list of reference vectors 
def retrieve_best_match(query, vector_db):
  query_embedding = ollama.embed(model=EMBEDDING_MODEL, input=query)['embeddings'][0]
  max_similarity = -1
  max_idx        = -1
  for idx in range(len(vector_db)):
     similarity = 0
     chunk, embedding = vector_db[idx]
     similarity = cosine_similarity(query_embedding, embedding)
     if similarity > max_similarity:
        max_similarity = similarity
        max_idx =  idx
  return max_similarity, max_idx

# Calculating for every permulation is unbiased but slow.
# Should probably limit number of responses or use different algorithm for large number of responses.
def retrieve_max_permutation(queries, vector_db):
  num_refs    = len(vector_db)
  num_queries = len(queries)
  cost_matrix = np.zeros((num_refs, num_refs))
  query_embeddings = []
  for q in queries:
     query_embeddings.append(ollama.embed(model=EMBEDDING_MODEL, input=q)['embeddings'][0])

  for i in range(num_queries):
     for j in range(num_refs):
        chunk, embedding = vector_db[j]
        similarity = cosine_similarity(query_embeddings[i], embedding)
        cost_matrix[i,j] = 1.0 - similarity
  row_ind, col_ind = linear_sum_assignment(cost_matrix) 
  print(row_ind)
  print(col_ind)  
  # Store similarities for each query for best permutation
  similarities = []
  for idx, q in enumerate(query_embeddings):
     chunk, embedding = vector_db[col_ind[idx]]
     similarities.append(cosine_similarity(q, embedding))

  return similarities, col_ind 
