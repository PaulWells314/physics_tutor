from flask import Flask, render_template, request, session, redirect
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
   if request.method == 'POST':
      selected_option =  request.form.get('options')
      # Load button
      if request.form.get('submit_button') == "load":
          with open(selected_option) as fin:
             data = json.load(fin)
             session['data'] = data['request_list'] 
             session['obj_index'] = 0
             init_context(session)
             session['selected'] = selected_option
             obj = session['data'][session['obj_index']]
             # Description of problem at start of json
             session['context']['problem_txt'] = data["description"]
             # First request 
             if "request" in obj:
                session['context']['request_txt'] = obj["request"] 
             session.modified = True
             return render_template('index.html', context = session['context'])
   elif request.method == "GET":
      if 'context' not in session:
         session['obj_index'] = 0
         init_context(session) 
         session['selected'] = ""
      return render_template('index.html', context = session['context'])
@app.route('/dialog', methods = ['POST', 'GET'])
def dialog():
   # Return from canvas?
   if request.referrer and request.referrer.split("/")[-1] == "canvas":
      return render_template('dialog.html', context = session['context'])
   
   if request.method == 'POST':
      if 'data' not in session:
         session['context']['color'] = 'orange'
         session['context']['comment_txt'] = "Use Load to load problem!"
         session.modified = True
         return render_template('dialog.html', context = session['context'])

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
         return render_template('dialog.html', context = session['context'])
      # Previous button
      if request.form.get('submit_button') == "previous":
         if session['obj_index'] > 0:
            session['obj_index'] = session['obj_index'] - 1
            obj = session['data'][session['obj_index']]
            session['context']['request_txt'] = obj["request"]
            session['context']['comment_txt'] = "" 
         else:
            session['context']['comment_txt'] = "First Question" 
         session['context']['response_txt'] = ""
         session.modified = True
         return render_template('dialog.html', context = session['context'])
      # Delete button
      if request.form.get('submit_button') == "delete":
         if len(session['data']) == 0:
            pass
         elif session['obj_index'] < len(session['data']) - 1:
            del(session['data'][session['obj_index']])
            if len(session['data']) != 0:
               obj = session['data'][session['obj_index']]
               session['context']['request_txt'] = obj["request"]
            else:
               session['context']['request_txt'] = ""
            session['context']['comment_txt'] = "" 
         else:
            del(session['data'][session['obj_index']])            
            if len(session['data']) != 0:
               session['obj_index'] = session['obj_index'] - 1
               obj = session['data'][session['obj_index']]
               session['context']['request_txt'] = obj["request"]
            else:
               session['context']['request_txt'] = ""
            session['context']['comment_txt'] = "" 
         session['context']['response_txt'] = ""
         session.modified = True
         return render_template('dialog.html', context = session['context'])
      # Insert button
      if request.form.get('submit_button') == "insert":
         new_obj = {}
         new_obj["type"] = "all"
         new_obj["request"] = "test"
         new_obj["responses"] = []
         new_obj["responses"].append("test_response")
         session['data'].insert(session['obj_index'], new_obj)
         obj = session['data'][session['obj_index']]
         session['context']['request_txt'] = obj["request"]
         session.modified = True
         return render_template('dialog.html', context = session['context'])
      # Submit button  
      if request.form.get('submit_button') == "submit":
         obj = session['data'][session['obj_index']]
         # Submit before Next? 
         if 'request' not in obj:
               session['context']['color'] = 'orange'
               session['context']['comment_txt'] = "Please press Next before Submit" 
               session.modified = True
               return render_template('dialog.html', context = session['context'])
         vector_db = []
         comment_txt=""
         req_type = obj["type"]
         session['context']['color'] = 'black'
         session['context']['response_txt'] = request.form.get('response_text')
         user_str = session['context']['response_txt'].rstrip()
         if req_type == "all":
            # Add all possible model responses to request to vector database
            user_responses = user_str.splitlines() 
            for response_item in obj["responses"]:
               vector_db = ml.add_chunk_to_database(response_item, vector_db)
            # Too many user responses?
            if len(user_responses) > len(vector_db):
               comment_txt += "too many user responses"
               session['context']['color'] = 'red'
            else:
               similarities, perm = ml.retrieve_max_permutation(user_responses, vector_db)
               for idx, resp in enumerate(user_responses):
                  comment_txt += "student: {0} ai: {1} score: {2:1.3f}\n".format(resp, obj["responses"][perm[idx]], similarities[idx])
                  if similarities[idx] <= 0.8:
                     session['context']['color'] = 'red'
               # Missing user responses?
               if len(user_responses) < len(vector_db):
                  for idx in range(len(user_responses), len(vector_db)):
                     session['context']['color'] = 'red'
                     comment_txt += "missing response: {0}\n".format(obj["responses"][perm[idx]])         
         if req_type == "paint":
            #Empty input?
            if user_str == "":
                comment_txt += "Empty response!  Please try again!"
                session['context']['comment_txt'] = comment_txt
                session['context']['color'] = 'orange'
                session.modified = True
                return render_template('dialog.html', context = session['context'])
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
               session['context']['color'] = 'orange'
               comment_txt = "mistake in equation format (need to use * for all multiplies)"
            except Exception as e:
               session['context']['color'] = 'orange'
               comment_txt = "equation error"
            else:
                if 0 == (user_eqn-ref_eqn):
                   comment_txt = "equation matches {0}".format(obj["equation"])
                else:
                   session['context']['color'] = 'red'
                   comment_txt = "equation does not match {0}".format(obj["equation"])
         if req_type == "vectors":
            # Use canvas to create vectors
            if 'vectors' not in session['context']:
               comment_txt = "Use Canvas to create vectors!"
               session['context']['color'] = 'orange'
               session['context']['comment_txt'] = comment_txt
               session.modified = True
               return render_template('dialog.html', context = session['context'])
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
            # Too many user responses?
            if len(user_responses) > len(references):  
               session['context']['color'] = 'red'
               comment_txt += "Too many user vectors"
               session['context']['comment_txt'] = comment_txt
               session.modified = True
               return render_template('dialog.html', context = session['context'])
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
               if sim <= 0.8:
                  session['context']['color'] = 'red'
               comment_txt += "student: {0} ref: {1} word score: {2:1.3f} physical vector score: {3:1.3f}\n".format(resp, references[pidx], similarities[idx], sim)
            # Missing user responses?
            if len(user_responses) < len(references):  
               session['context']['color'] = 'red'
               for idx in range(len(user_responses), len(vector_db)):
                  comment_txt += "missing response: {0}\n".format(references[perm[idx]])
         if req_type == "graph":
            # Use graph to create graph lines 
            if 'graph_lines' not in session['context']:
               comment_txt = "Use Graph to create graph line!"
               session['context']['color'] = 'orange'
               session['context']['comment_txt'] = comment_txt
               session.modified = True
               return render_template('dialog.html', context = session['context'])
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
            def graph_parse_array(f, y, threshold):
               if abs(y) <= threshold:
                  f.append(0)
               elif y > 0:
                  f.append(1)
               else:
                  f.append(-1)  
            print(session['context']['graph_lines'])
            user_line_num = len(session['context']['graph_lines'])
            ref_line_num  = len(obj["responses"]) 
            if user_line_num != ref_line_num:
               session['context']['color'] = 'red'
               comment_txt = comment_txt + "number of captured lines does not equal number of expected lines"
               session['context']['comment_txt'] = comment_txt
               session.modified = True
               return render_template('dialog.html', context = session['context']) 
            for index, line in enumerate(session['context']['graph_lines']):
               for segment in line:
                  if segment["x2"] ==  segment["x1"]:
                     comment_txt += "segment zero delta x not supported: repeat point or infinite gradient"
                     session['context']['color'] = 'orange'
                     session['context']['comment_txt'] = comment_txt
                     session.modified = True
                     return render_template('dialog.html', context = session['context'])
               f0 = []
               for segment in line:
                  graph_parse_array(f0, segment["y1"], 2)
               f0_filtered = graph_unique_array(f0)
               print(f0_filtered)
               print(obj["responses"][index])
               if f0_filtered ==  obj["responses"][index]["f0"]:
                  comment_txt = comment_txt + " f0 match"
               else:
                  session['context']['color'] = 'red'
                  comment_txt = comment_txt + " f0 mismatch"
               #first derivative 
               f1 = []
               grads = []
               deltas = []
               for segment in line:
                  g = (segment["y2"] - segment["y1"])/(segment["x2"] - segment["x1"])
                  graph_parse_array(f1, g, 0.01)
                  grads.append(g)
                  deltas.append((segment["x2"] + segment["x1"])/2.0)
               f1_filtered = graph_unique_array(f1)
               print(f1_filtered)
               print(obj["responses"][index])
               if f1_filtered ==  obj["responses"][index]["f1"]:
                  comment_txt = comment_txt + " f1 match"
               else: 
                  session['context']['color'] = 'red'
                  comment_txt = comment_txt + " f1 mismatch"
               #second derivative
               f2 = []
               second_derivatives = [] 
               for i,grad in enumerate(grads[0:-1]):
                  second_derivatives.append((grads[i+1]-grads[i])/(deltas[i+1]-deltas[i]))
               for second_derivative in second_derivatives:
                  graph_parse_array(f2, second_derivative, 0.0001)
               f2_filtered = graph_unique_array(f2)
               print(f2_filtered)
               print(obj["responses"][index])
               if f2_filtered ==  obj["responses"][index]["f2"]:
                  comment_txt = comment_txt + " f2 match"
               else:
                  session['context']['color'] = 'red'
                  comment_txt = comment_txt + " f2 mismatch"

         session['context']['comment_txt'] = comment_txt
         session.modified = True
         return render_template('dialog.html', context = session['context'])

   elif request.method == "GET":
      if 'context' not in session:
         session['obj_index'] = 0
         init_context(session) 
         session['selected'] = ""
            
      return render_template('dialog.html', context = session['context'])
 
@app.route('/canvas')
def canvas():
   if 'data' not in session:
      session['context']['comment_txt'] = "Use Load to load problem!"
      session['context']['color'] = 'orange'
      session.modified = True
      return redirect('/dialog')
   obj = session['data'][session['obj_index']]
   if 'canvas_background' in obj:
      background = obj['canvas_background']
      return render_template('canvas.html', bg=background)
   else:
      session['context']['comment_txt'] = "Canvas not supported for this question!"
      session['context']['color'] = 'orange'
      session.modified = True
      return redirect('/dialog')
 
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
