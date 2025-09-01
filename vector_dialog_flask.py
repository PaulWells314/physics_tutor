from flask import Flask, render_template, request, session, redirect
import json
import math
import sys
import time
import os
import argparse
import ml
import sympy
import numpy as np
from sympy import *

app = Flask(__name__)
app.secret_key = 'purple_parrot'

def init_context(session):
    session['context'] = {}
    session['context']['problem_txt'] = ""
    session['context']['request_txt'] = ""
    session['context']['response_txt'] = ""
    session['context']['comment_txt'] = ""
    directory_path = './problems'
    session['context']['files'] = os.listdir(directory_path)
    return
   
@app.route('/', methods = ['POST', 'GET'])
def init():
   selected_option =  request.form.get('options')
   session['mode']   =  request.form.get('mode')
   session.permanent = True
   if request.method == 'POST':
      # Load button
      if request.form.get('submit_button') == "load":
          filename = "./problems/" + selected_option
          with open(filename) as fin:
             data = json.load(fin)
             session['data'] = data['request_list'] 
             session['answers'] = ["" for i in range(len(data['request_list']))]
             session['obj_index'] = 0
             init_context(session)
             session['selected'] = selected_option
             obj = session['data'][session['obj_index']]
             # Description of problem at start of json
             session['context']['problem_txt'] = data["description"]
             # First request 
             if "request" in obj:
                session['context']['request_txt'] = obj["request"] 
      # New button
      if request.form.get('new_button') == "new": 
         session['answers'] = []
         session['data']    = []
         session['obj_index'] = 0
         session['mode'] = 'teacher'
         init_context(session) 
         session.modified = True
      return render_template('index.html', context = session['context'], disp = session['mode'])
   elif request.method == "GET":
      session['obj_index'] = 0
      if 'mode' not in session:
         session['mode'] = 'student'
      init_context(session) 
      session['selected'] = ""
      return render_template('index.html', context = session['context'], disp = session['mode'])
@app.route('/dialog', methods = ['POST', 'GET'])
def dialog():
   if 'mode' in session:
      if session['mode'] == 'teacher':
         disp = 'flex'
      else:
         disp = 'none'
   else:
      disp = 'none'
     
   # Return from canvas?
   if request.referrer and request.referrer.split("/")[-1] == "canvas":
      return render_template('dialog.html', context = session['context'], disp=disp)

   # Return from graph?
   if request.referrer and request.referrer.split("/")[-1] == "graph":
      return render_template('dialog.html', context = session['context'], disp=disp)
   
   if request.method == 'POST':
      if 'data' not in session:
         session['data'] = []
         session['answers'] = []
         init_context(session)
         session['context']['comment_txt'] = "Problem not loaded: creating from scratch"
         session.modified = True

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
         return render_template('dialog.html', context = session['context'], disp = disp)
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
         return render_template('dialog.html', context = session['context'], disp = disp)
      # Delete button
      if request.form.get('submit_button') == "delete":
         if len(session['data']) == 0:
            pass
         elif session['obj_index'] < len(session['data']) - 1:
            del(session['data'][session['obj_index']])
            del(session['answers'][session['obj_index']])
            if len(session['data']) != 0:
               obj = session['data'][session['obj_index']]
               session['context']['request_txt'] = obj["request"]
            else:
               session['context']['request_txt'] = ""
            session['context']['comment_txt'] = "" 
         else:
            del(session['data'][session['obj_index']])            
            del(session['answers'][session['obj_index']])            
            if len(session['data']) != 0:
               session['obj_index'] = session['obj_index'] - 1
               obj = session['data'][session['obj_index']]
               session['context']['request_txt'] = obj["request"]
            else:
               session['context']['request_txt'] = ""
            session['context']['comment_txt'] = "" 
         session['context']['response_txt'] = ""
         session.modified = True
         return render_template('dialog.html', context = session['context'], disp = disp)
      # Insert button
      if request.form.get('submit_button') == "insert":
         new_obj = {}
         new_obj["type"] = "all"
         new_obj["request"] = ""
         new_obj["responses"] = []
         session['data'].insert(session['obj_index'], new_obj)
         session['answers'].insert(session['obj_index'], "")
         obj = session['data'][session['obj_index']]
         session['context']['request_txt'] = obj["request"]
         session['context']['type'] = new_obj["type"]
         session.modified = True
         return render_template('dialog.html', context = session['context'], disp = disp)
      # Append button
      if request.form.get('submit_button') == "append":
         new_obj = {}
         new_obj["type"] = "all"
         new_obj["request"] = ""
         new_obj["responses"] = []
         session['data'].append(new_obj)
         session['answers'].append("")
         session['obj_index'] = len(session['data']) - 1
         obj = session['data'][session['obj_index']]
         session['context']['request_txt'] = obj["request"]
         session['context']['type'] = new_obj["type"]
         session.modified = True
         return render_template('dialog.html', context = session['context'], disp = disp)
      # Submit button  
      if request.form.get('submit_button') == "submit":
         obj = session['data'][session['obj_index']]
         # Submit before Next? 
         if 'request' not in obj:
               session['context']['color'] = 'orange'
               session['context']['comment_txt'] = "Please press Next before Submit" 
               session.modified = True
               return render_template('dialog.html', context = session['context'], disp = disp)
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
                return render_template('dialog.html', context = session['context'], disp = disp)
            if "responses" in obj: 
               for response in obj["responses"]:
                  response_text    = response["text"]
                  response_comment = response["comment"]
                  response_mask    = response["mask"]
                  vector_db = ml.add_chunk_to_database(response_text, vector_db)  
               similarity, idx = ml.retrieve_best_match(user_str, vector_db)
               comment_txt = obj["responses"][idx]["comment"] 
         if req_type == "equation":
            # Current restriction to one equation per question
            eqn_txt =  obj["responses"][0]
            ref_eqn  = sympify(eqn_txt)
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
                   comment_txt = "equation matches {0}".format(eqn_txt)
                else:
                   session['context']['color'] = 'red'
                   comment_txt = "equation does not match {0}".format(eqn_txt)
         if req_type == "expression":
            comment_txt = ""
            user_responses = user_str.splitlines()
            splitter = ""
            for sp in ['=', '<', '>']:
               if sp in obj["responses"][0]:
                  splitter = sp 
            num_user = len(user_responses)
            num_ref  = len(obj["responses"])
            if num_user > num_ref:
               session['context']['color'] = 'red'
               comment_txt += "too many user equations\n" 
            else:
               ref_mask = np.zeros(num_ref)
               for  user_eqn in user_responses:  
                  #splitter missing?
                  if (splitter != "") and (-1 == user_eqn.find(splitter)):
                     session['context']['color'] = 'orange'
                     comment_txt += " " + splitter + " not present!"
                     continue
                  is_match = False
                  for index, eqn_txt in enumerate(obj["responses"]):
                     if splitter == "":
                        eqn_txt_l = eqn_txt
                        user_eqn_l = user_eqn
                        eqn_txt_r  = ""
                        user_eqn_r = "" 
                     else: 
                        eqn_txt_l  = "".join(eqn_txt.split(splitter)[0])  
                        user_eqn_l = "".join(user_eqn.split(splitter)[0])
                        eqn_txt_r  = "".join(eqn_txt.split(splitter)[1])  
                        user_eqn_r = "".join(user_eqn.split(splitter)[1]) 
                     ref_eqn_l  = sympify(eqn_txt_l)
                     ref_expr_l  = srepr(ref_eqn_l)
                     if splitter != "":
                        ref_eqn_r  = sympify(eqn_txt_r)
                        ref_expr_r  = srepr(ref_eqn_r)
                     else:
                        ref_expr_r = ""
                     try:
                        user_expr_l = srepr(sympify(user_eqn_l))
                        if splitter != "":
                           user_expr_r = srepr(sympify(user_eqn_r))
                        else:
                           user_expr_r = ""
                     except SympifyError:
                        session['context']['color'] = 'orange'
                        comment_txt += "mistake in equation format (need to use * for all multiplies)"
                     except Exception as e:
                        session['context']['color'] = 'orange'
                        comment_txt += "equation error"
                     else:
                        if (user_expr_l == ref_expr_l) and (user_expr_r == ref_expr_r) and (ref_mask[index] == 0) :
                           is_match = True
                           ref_mask[index] = 1
                        else:
                           pass
                  if is_match:
                     comment_txt += "equation {0} matches\n".format(user_eqn)
                  else:
                     session['context']['color'] = 'red'
                     comment_txt += "equation {0} does not match\n".format(user_eqn)
               if num_user < num_ref:
                  session['context']['color'] = 'red'
                  comment_txt += "too few  user equations\n" 
         if req_type == "vectors":
            # Use canvas to create vectors
            if 'vectors' not in session['context']:
               comment_txt = "Use Canvas to create vectors!"
               session['context']['color'] = 'orange'
               session['context']['comment_txt'] = comment_txt
               session.modified = True
               return render_template('dialog.html', context = session['context'], disp = disp)
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
               return render_template('dialog.html', context = session['context'], disp = disp)
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
               return render_template('dialog.html', context = session['context'], disp = disp)
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
            user_line_num = len(session['context']['graph_lines'])
            ref_line_num  = len(obj["responses"]) 
            if user_line_num != ref_line_num:
               session['context']['color'] = 'red'
               comment_txt = comment_txt + "number of captured lines does not equal number of expected lines"
               session['context']['comment_txt'] = comment_txt
               session.modified = True
               return render_template('dialog.html', context = session['context'], disp = disp) 
            for index, line in enumerate(session['context']['graph_lines']):
               for segment in line:
                  if segment["x2"] ==  segment["x1"]:
                     comment_txt += "segment zero delta x not supported: repeat point or infinite gradient"
                     session['context']['color'] = 'orange'
                     session['context']['comment_txt'] = comment_txt
                     session.modified = True
                     return render_template('dialog.html', context = session['context'], disp = disp)
               f0 = []
               for segment in line:
                  graph_parse_array(f0, segment["y1"], 2)
               f0_filtered = graph_unique_array(f0)
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
               if f2_filtered ==  obj["responses"][index]["f2"]:
                  comment_txt = comment_txt + " f2 match"
               else:
                  session['context']['color'] = 'red'
                  comment_txt = comment_txt + " f2 mismatch"

         session['context']['comment_txt'] = comment_txt
         session['answers'][session['obj_index']] = session['context']['response_txt']
         print(session['answers'])
         session.modified = True
         return render_template('dialog.html', context = session['context'], disp = disp)

   elif request.method == "GET":
      if 'context' not in session:
         session['obj_index'] = 0
         init_context(session) 
         session['selected'] = ""
            
      return render_template('dialog.html', context = session['context'], disp = disp)
 
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
@app.route('/edit', methods = ['POST', 'GET'])
def edit():
   if request.method == 'POST':
       if request.form.get('submit_button') == "save_problem": 
          session['context']['problem_txt'] = request.form.get('problem_text').strip()
          session.modified = True
       if request.form.get('submit_button') == "save_question": 
          session['context']['request_txt'] = request.form.get('question_text').strip()
          session['context']['type'] = request.form.get('type_txt').strip()
          session['data'][session['obj_index']]["type"] = session['context']['type']
          session['data'][session['obj_index']]["request"] = session['context']['request_txt'].strip()
          session.modified = True
       if request.form.get('submit_button') == "save_response": 
          if "responses" not in session['data'][session['obj_index']]:
             session['data'][session['obj_index']]["responses"] = []
          session['data'][session['obj_index']]["responses"].append(request.form.get('response_text').strip())
          session.modified = True
       if request.form.get('submit_button') == "delete_responses": 
          session['data'][session['obj_index']]["responses"] = []
          session['context']['response_txt'] = ""
          session.modified = True
   elif request.method == 'GET':
      if 'data' not in session:
          session['context']['comment_txt'] = "No data"
          session['context']['color'] = 'orange'
          session.modified = True
          return redirect('/dialog')
      elif not session['data']:
          session['context']['comment_txt'] = "Empty data"
          session['context']['color'] = 'orange'
          session.modified = True
          return redirect('/dialog')
   responses = ""
   if 'data' in session and "responses" in session['data'][session['obj_index']]:
      responses = json.dumps(session['data'][session['obj_index']]["responses"]) 
   return render_template('edit.html', context = session['context'], responses = responses)
@app.route('/store', methods = ['POST', 'GET'])
def store():
   if request.method == 'POST':
      filename = request.form.get('filename')
      filename ="./problems/" + filename
      with open(filename, "w") as json_file:
         out_dict = {}
         out_dict['description'] = session['context']['problem_txt']
         out_dict['request_list'] = session['data']
         json.dump(out_dict, json_file, indent=4)
   return render_template('store.html', context = session['context'])
