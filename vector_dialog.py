# A program to load a json file with request/response pairs, present request, read response,
# store in a vector database, and compare with json response.
# There may be multiple response lines for a request in which case the program will try all possible
# permutations of the json responses and select the one with the maximum total score.
import json
from openai import OpenAI
import math
import sys
import ollama
import time
from itertools import permutations

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

# Calculating for every permulation is unbiased but slow.
# Should probably limit number of responses or use different algorithm for large number of responses.
def retrieve_max_permutation(queries, vector_db):
  query_embeddings = []
  for q in queries:
     query_embeddings.append(ollama.embed(model=EMBEDDING_MODEL, input=q)['embeddings'][0])
  perms = permutations(list(range(len(vector_db))))
  max_similarity = -1
  max_p          = -1
  for p in perms:
     similarity = 0
     for idx, q in enumerate(query_embeddings):
        chunk, embedding = vector_db[p[idx]]
        similarity = similarity + cosine_similarity(q, embedding)
     if similarity > max_similarity:
        max_similarity = similarity
        max_p = p
  # Store similarities for each query for best permutation
  similarities = []
  for idx, q in enumerate(query_embeddings):
     chunk, embedding = vector_db[max_p[idx]]
     similarities.append(cosine_similarity(q, embedding))
  
  return similarities, max_p

# Load all requests and model responses from json file
if len(sys.argv) != 2:
   print("Use: python vector_dialog.py <json file path>")
   sys.exit()
with open(sys.argv[1]) as fin:
   data = json.load(fin)
for obj in data:
   print(obj["request"])
   vector_db = []
   # Add all possible model responses to request to vector database
   for response_item in obj["response"]:
      vector_db = add_chunk_to_database(response_item, vector_db)
   # Ask user for responses. One line per response
   user_responses = []
   print("Input response. Enter q to finish")
   while True:
      user_str = input()
      if user_str == "q":
         break
      user_responses.append(user_str)
   similarities, perm = retrieve_max_permutation(user_responses, vector_db)
   for idx, resp in enumerate(user_responses):
      print("student: {0} ai: {1} score: {2:1.3f}".format(resp, obj["response"][perm[idx]], similarities[idx]))
