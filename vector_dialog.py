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
import argparse

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
parser = argparse.ArgumentParser()
parser.add_argument("json_file")
parser.add_argument("-r", "--repeat", help="repeat question if wrong or partial answer given", action="store_true")
args = parser.parse_args()
print(args.json_file)
with open(args.json_file) as fin:
   data = json.load(fin)
req_type = ""
for obj in data:
   if "description" in obj:
      print("")
      print(obj["description"])
      print("")
   if "request" in obj:
      print(obj["request"])
   if "type" in obj:
      req_type= obj["type"]
   if "responses" in obj:
      vector_db = []
      if req_type=="all":
         # Add all possible model responses to request to vector database
         for response_item in obj["responses"]:
            vector_db = add_chunk_to_database(response_item, vector_db)
         # Ask user for responses. One line per response
         user_responses = []
         if len(obj["responses"]) == 1:
            print("Input response (single line answer).")
         else:
            print("Input responses (1 line per response). Enter q to finish")
         while True:
            user_str = input()
            if user_str == "q":
               break
            user_responses.append(user_str)
            # single line answer?
            if len(obj["responses"]) == 1:
               break
         similarities, perm = retrieve_max_permutation(user_responses, vector_db)
         for idx, resp in enumerate(user_responses):
            print("student: {0} ai: {1} score: {2:1.3f}".format(resp, obj["responses"][perm[idx]], similarities[idx]))
         # Missing user responses?
         if len(user_responses) < len(vector_db):
            for idx in range(len(user_responses), len(vector_db)):
               print("missing response: {0}".format(obj["responses"][perm[idx]]))
      # Find best match for single input (which may not be best answer!) and make comment
      if req_type=="paint":
         for response in obj["responses"]:
            response_text    = response["text"]
            response_comment = response["comment"]
            response_mask    = response["mask"] 
            vector_db = add_chunk_to_database(response_text, vector_db)
         while True:
            user_str = input()
            similarity, idx = retrieve_best_match(user_str, vector_db)
            print(obj["responses"][idx]["comment"])
            if (args.repeat == False) or user_str=="q" or obj["responses"][idx]["mask"] == obj["total_mask"]:
               break
