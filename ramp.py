from vpython import *
from openai import OpenAI
import math
import sys
import ollama

# Load the dataset

dataset = []
with open('ramp_1.txt', 'r') as file:
  dataset = file.readlines()
  print(f'Loaded {len(dataset)} entries')

# Implement the retrieval system

EMBEDDING_MODEL = 'hf.co/CompendiumLabs/bge-base-en-v1.5-gguf'
LANGUAGE_MODEL = 'hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF'

# Each element in the VECTOR_DB will be a tuple (chunk, embedding)
# The embedding is a list of floats, for example: [0.1, 0.04, -0.34, 0.21, ...]
VECTOR_DB = []

def add_chunk_to_database(chunk):
  embedding = ollama.embed(model=EMBEDDING_MODEL, input=chunk)['embeddings'][0]
  VECTOR_DB.append((chunk, embedding))

for i, chunk in enumerate(dataset):
  add_chunk_to_database(chunk)
  print(f'Added chunk {i+1}/{len(dataset)} to the database')

def cosine_similarity(a, b):
  dot_product = sum([x * y for x, y in zip(a, b)])
  norm_a = sum([x ** 2 for x in a]) ** 0.5
  norm_b = sum([x ** 2 for x in b]) ** 0.5
  return dot_product / (norm_a * norm_b)

def retrieve(query, top_n=3):
  query_embedding = ollama.embed(model=EMBEDDING_MODEL, input=query)['embeddings'][0]
  # temporary list to store (chunk, similarity) pairs
  similarities = []
  for chunk, embedding in VECTOR_DB:
    similarity = cosine_similarity(query_embedding, embedding)
    similarities.append((chunk, similarity))
  # sort by similarity in descending order, because higher similarity means more relevant chunks
  similarities.sort(key=lambda x: x[1], reverse=True)
  # finally, return the top N most relevant chunks
  return similarities[:top_n]

scene.width = scene.height = 600
scene.range = 5 
scene.title = "Block on ramp"
scene.up    = vec(0, 1, 0)

p = "A block is stationary on a ramp. The ramp is at an angle of 30 degrees to the horizontal. The block is resting unattached on the ramp.\n"
p +="What forces are acting on the block? Give the magnitude and direction for each force. Introduce and define symbols for any undefined quantities. \n" 

scene.caption = p

#ramp has angle of 30 degrees
theta = math.pi/6.0

ramp  = box( opacity=0.5, pos=vec(0, 0, 0), axis = vec(math.cos(theta), math.sin(theta), 0), length =4, height=0.5, width=4, color=color.cyan)
brick = box( opacity=0.5, pos=vec(-0.5*math.sin(theta), 0.5*math.cos(theta), 0), axis = vec(math.cos(theta), math.sin(theta), 0), length=0.5, height=0.5, width=0.5, color=color.red)
print("What forces are acting on block?")
user_input = input()
scene.caption = user_input

# check response against stored embedded vectors
retrieved_knowledge = retrieve(user_input)
for chunk, similarity in retrieved_knowledge:
  print(f' - (similarity: {similarity:.2f}) {chunk}')

wt = arrow(shaftwidth=0.05, pos=vec(-0.5*math.sin(theta), 0.5*math.cos(theta), 0), axis=vec(0, -4, 0), round = True, color=color.orange)

# deepseek  answer
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key="API_KEY",
)
#messages = [{"role": "user", "content": "Solve this problem.  "+p}]
#response = client.chat.completions.create(
#    model="deepseek/deepseek-r1:free",
#    messages=messages
#)

#messages.append(response.choices[0].message)
#print(response.choices[0].message.content)
#scene.caption = str(response.choices[0].message.content) 
#user_input = input()

# ask socratic questions about this problem 
#messages = [{"role": "user", "content": "Ask socratic questions about this problem"}]
#
#response = client.chat.completions.create(
#    model="deepseek/deepseek-r1:free",
#    messages=messages
#)

#messages.append(response.choices[0].message)
#
#print(response.choices[0].message.content)
#scene.caption = str(response.choices[0].message.content)
