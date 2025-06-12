from flask import Flask, render_template, request, session
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

app = Flask(__name__)
app.secret_key = 'purple_parrot'
   
@app.route('/', methods = ['POST', 'GET'])
def hello():
   if request.method == 'POST':
      session['context']['response_txt'] = request.form.get('response_text')
      obj = session['data'][session['obj_index']]
      vector_db = []
      comment_txt=""
      user_str = session['context']['response_txt'].rstrip()
      req_type = obj["type"]
      print(user_str)
      if user_str == 'q':
         session['obj_index'] = session['obj_index'] + 1
         obj = session['data'][session['obj_index']]
         session['context']['request_txt'] = obj["request"] 
         return render_template('index.html', context = session['context'])
      if req_type == "all":
      # Add all possible model responses to request to vector database
         user_responses = user_str.splitlines() 
         for response_item in obj["responses"]:
            vector_db = add_chunk_to_database(response_item, vector_db)
         similarities, perm = retrieve_max_permutation(user_responses, vector_db)
         for idx, resp in enumerate(user_responses):
            comment_txt += "student: {0} ai: {1} score: {2:1.3f}".format(resp, obj["responses"][perm[idx]], similarities[idx])
         # Missing user responses?
         if len(user_responses) < len(vector_db):
            for idx in range(len(user_responses), len(vector_db)):
               comment_txt += "missing response: {0}".format(obj["responses"][perm[idx]])         
      if req_type == "paint":
         if "responses" in obj: 
            for response in obj["responses"]:
               response_text    = response["text"]
               response_comment = response["comment"]
               response_mask    = response["mask"]
               vector_db = add_chunk_to_database(response_text, vector_db)  
            similarity, idx = retrieve_best_match(user_str, vector_db)
            comment_txt = obj["responses"][idx]["comment"] 
      session['context']['comment_txt'] = comment_txt
      return render_template('index.html', context = session['context'])
   else:
      with open("ramp.json") as fin:
         if 'data' not in session:
            session['data'] = json.load(fin)
            session['obj_index'] = 0 
            session['context'] = {}
            session['context']['problem_txt'] = ""
            session['context']['request_txt'] = ""
            session['context']['response_txt'] = ""
            session['context']['comment_txt'] = ""
            obj = session['data'][session['obj_index']]
            if "description" in obj:
               session['context']['problem_txt'] = obj["description"] 
               session['obj_index'] = session['obj_index'] + 1
               obj = session['data'][session['obj_index']]
            if "request" in obj:
               session['context']['request_txt'] = obj["request"] 
            
      return render_template('index.html', context = session['context'])
