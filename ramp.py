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

def filter_out_think(text):
  s = "</think>"
  index = text.find(s)
  if index != -1:
    filtered = text[index+len(s):]
  else:
    filtered = text
  return filtered

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
print("What forces are acting on block? Press Enter after describing each force and type Exit and press Enter when finished.")
while(True):
   user_input = input()
   if user_input=="Exit":
      break
   scene.caption = user_input

   # check response against stored embedded vectors
   retrieved_knowledge = retrieve(user_input)
   chunk, similarity = retrieved_knowledge[0]
   print(f' - (similarity: {similarity:.2f}) {chunk}')

wt = arrow(shaftwidth=0.05, pos=vec(-0.5*math.sin(theta), 0.5*math.cos(theta), 0), axis=vec(0, -4, 0), round = True, color=color.orange)
fr = arrow(shaftwidth=0.05, pos=vec(-0.25*math.sin(theta), 0.25*math.cos(theta), 0), axis = vec(4*math.cos(theta),4* math.sin(theta), 0), round = True, color=color.orange)
r  = arrow(shaftwidth=0.05, pos=vec(-0.25*math.sin(theta), 0.25*math.cos(theta), 0), axis=vec(-4*math.sin(theta), 4*math.cos(theta), 0), round = True, color=color.orange)

wt_l = label(align='left', xoffset = 20, line=False, pos=vec(-0.5*math.sin(theta), 0.5*math.cos(theta)-4, 0), text='Weight', box=False)
fr_l = label(align='left', xoffset = 20, line=False, pos=vec(-0.25*math.sin(theta)+4*math.cos(theta), 0.25*math.cos(theta)+4* math.sin(theta), 0), text='Friction', box=False)
r_l  = label(align='left', xoffset = 20, line=False, pos=vec(-0.25*math.sin(theta)-4*math.sin(theta), 0.25*math.cos(theta)+4* math.cos(theta), 0), text='Reaction', box=False)

# deepseek  answer
m = [{"role": "user", "content": p}]
response = ollama.chat(
        model="deepseek-r1",
        messages=m
    )
r = filter_out_think(response["message"]["content"])
scene.caption = r 
print("Enter to generate socratic questions")
user_input = input()
p = " Ask socratic questions about a block stationary on a ramp. Only ask socratic questions and do not answer any of these questions. Output should be a numbered list of questions."
m = [{"role": "user", "content": p}]

# ask socratic questions about this problem 
response = ollama.chat(
        model="deepseek-r1",
        messages=m
    )
r = filter_out_think(response["message"]["content"])
scene.caption = r 
print(r)
