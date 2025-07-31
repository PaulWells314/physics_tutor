from flask import Flask, render_template, request, session
import json
import math
import sys
import time
import argparse
import ml
import sympy
from sympy import *

app = Flask(__name__)
app.secret_key = 'purple_parrot'

def init_context(session):
    session['context'] = {}
    session['context']['problem_txt'] = ""
    session['context']['request_txt'] = ""
    session['context']['response_txt'] = ""
    session['context']['comment_txt'] = ""
    return
   
@app.route('/', methods = ['POST', 'GET'])
def init():
   # Return from canvas?
   if request.referrer and request.referrer.split("/")[-1] == "canvas":
      return render_template('index.html', context = session['context'])
   
   if request.method == 'POST':
      selected_option =  request.form.get('options')
      # Load button
      if request.form.get('submit_button') == "load":
          with open(selected_option) as fin:
             session['data'] = json.load(fin)
             session['obj_index'] = 0
             init_context(session)
             session['selected'] = selected_option
             obj = session['data'][session['obj_index']]
             # Description of problem at start of json
             if "description" in obj:
                session['context']['problem_txt'] = obj["description"]
                session['obj_index'] = session['obj_index'] + 1
                obj = session['data'][session['obj_index']]
                # First request 
                if "request" in obj:
                   session['context']['request_txt'] = obj["request"] 
             session.modified = True
             return render_template('index.html', context = session['context'])
      # Next button
      if request.form.get('submit_button') == "next":
         if session['obj_index'] < len(session['data']) - 1:
            session['obj_index'] = session['obj_index'] + 1
            obj = session['data'][session['obj_index']]
            session['context']['request_txt'] = obj["request"]
            session['context']['comment_txt'] = "" 
         else:
            session['context']['comment_txt'] = "End of Questions" 
         session['context']['response_txt'] = ""
         session.modified = True
         return render_template('index.html', context = session['context'])
      # Submit button  
      if request.form.get('submit_button') == "submit":
         obj = session['data'][session['obj_index']]
         vector_db = []
         comment_txt=""
         req_type = obj["type"]
         session['context']['response_txt'] = request.form.get('response_text')
         user_str = session['context']['response_txt'].rstrip()
         if req_type == "all":
            # Add all possible model responses to request to vector database
            user_responses = user_str.splitlines() 
            for response_item in obj["responses"]:
               vector_db = ml.add_chunk_to_database(response_item, vector_db)
            similarities, perm = ml.retrieve_max_permutation(user_responses, vector_db)
            for idx, resp in enumerate(user_responses):
               comment_txt += "student: {0} ai: {1} score: {2:1.3f}\n".format(resp, obj["responses"][perm[idx]], similarities[idx])
            # Missing user responses?
            if len(user_responses) < len(vector_db):
               for idx in range(len(user_responses), len(vector_db)):
                  comment_txt += "missing response: {0}\n".format(obj["responses"][perm[idx]])         
         if req_type == "paint":
            if "responses" in obj: 
               for response in obj["responses"]:
                  response_text    = response["text"]
                  response_comment = response["comment"]
                  response_mask    = response["mask"]
                  vector_db = ml.add_chunk_to_database(response_text, vector_db)  
               similarity, idx = ml.retrieve_best_match(user_str, vector_db)
               comment_txt = obj["responses"][idx]["comment"] 
         if req_type == "equation":
            ref_eqn  = sympify(obj["equation"])
            try:
               user_eqn = sympify(user_str) 
            except SympifyError:
               comment_txt = "mistake in equation format (need to use * for all multiplies)"
            except Exception as e:
               comment_txt = "equation error"
            else:
                if 0 == (user_eqn-ref_eqn):
                   comment_txt = "equation matches {0}".format(obj["equation"])
                else:
                   comment_txt = "equation does not match {0}".format(obj["equation"])
         if req_type == "vectors":
            print(session['context']['vectors'])
            print(obj["responses"])
            comment_txt = ""
            # Add all possible model responses to request to vector database
            user_responses = []
            for u in session['context']['vectors']:
               user_responses.append(u['label']) 
            references = []
            for r in obj["responses"]:
               references.append(r['label'])
            for response_item in references:
               vector_db = ml.add_chunk_to_database(response_item, vector_db)
            similarities, perm = ml.retrieve_max_permutation(user_responses, vector_db)
            for idx, resp in enumerate(user_responses):
               pidx = perm[idx]
               ref_vec = []
               ref_vec.append(obj["responses"][pidx]["x"])
               ref_vec.append(obj["responses"][pidx]["y"])
               user_vec = []
               user_vec.append(session['context']['vectors'][idx]["x2"] - session['context']['vectors'][idx]["x1"])
               user_vec.append(session['context']['vectors'][idx]["y1"] - session['context']['vectors'][idx]["y2"])
               sim = ml.cosine_similarity(ref_vec, user_vec) 
               comment_txt += "student: {0} ref: {1} word score: {2:1.3f} physical vector score: {3:1.3f}\n".format(resp, references[pidx], similarities[idx], sim)
            # Missing user responses?
            if len(user_responses) < len(vector_db):
               for idx in range(len(user_responses), len(vector_db)):
                  comment_txt += "missing response: {0}\n".format(references[perm[idx]])
         if req_type == "graph":
            comment_txt = ""
            def graph_unique_array(f):
               is_first = True
               g = []
               for i in f:
                  if not is_first:
                     if i != i_prev:
                        g.append(i)
                  else:
                     is_first = False
                     g.append(i)
                  i_prev = i
               return g
            def graph_parse_array(f, y):
               if abs(y) <= 2:
                  f.append(0)
               elif y > 0:
                  f.append(1)
               else:
                  f.append(-1)  
            print(session['context']['graph_lines'])
            for index, line in enumerate(session['context']['graph_lines']):
               f0 = []
               for segment in line:
                  graph_parse_array(f0, segment["y1"])
               f0_filtered = graph_unique_array(f0)
               print(f0_filtered)
               print(obj["responses"][index])
               if f0_filtered ==  obj["responses"][index]["f0"]:
                  comment_txt = comment_txt + " f0 match"
               else:
                  comment_txt = comment_txt + " f0 mismatch"
             
               f1 = []
               for segment in line:
                  graph_parse_array(f1, segment["y2"] - segment["y1"])
               f1_filtered = graph_unique_array(f1)
               print(f1_filtered)
               print(obj["responses"][index])
               if f1_filtered ==  obj["responses"][index]["f1"]:
                  comment_txt = comment_txt + " f1 match"
               else:
                  comment_txt = comment_txt + " f1 mismatch"
         session['context']['comment_txt'] = comment_txt
         session.modified = True
         return render_template('index.html', context = session['context'])

   elif request.method == "GET":
      if 'context' not in session:
         session['obj_index'] = 0
         init_context(session) 
         session['selected'] = ""
            
      return render_template('index.html', context = session['context'])
 
@app.route('/canvas')
def canvas():
   return render_template('canvas.html') 
@app.route('/graph')
def graph():
   return render_template('graph.html') 
@app.route('/diagram', methods=['POST'])
def diagram():
   data = request.get_json()
   session['context']['vectors'] = data
   session.modified = True
   return "OK" 
@app.route('/graph_lines', methods=['POST'])
def graph_lines():
   data = request.get_json()
   session['context']['graph_lines'] = data
   session.modified = True
   return "OK" 
