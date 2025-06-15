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
             return render_template('index.html', context = session['context'])
      session['context']['response_txt'] = request.form.get('response_text')
      obj = session['data'][session['obj_index']]
      vector_db = []
      comment_txt=""
      user_str = session['context']['response_txt'].rstrip()
      req_type = obj["type"]
      # Next button
      if request.form.get('submit_button') == "next":
         if session['obj_index'] < len(session['data']) - 1:
            session['obj_index'] = session['obj_index'] + 1
            obj = session['data'][session['obj_index']]
            session['context']['request_txt'] = obj["request"]
         else:
            session['context']['comment_txt'] = "End of Questions" 
         return render_template('index.html', context = session['context'])

      # Submit button  
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
      session['context']['comment_txt'] = comment_txt
      return render_template('index.html', context = session['context'])

   elif request.method == "GET":
      if 'context' not in session:
         session['obj_index'] = 0
         init_context(session) 
         session['selected'] = ""
            
      return render_template('index.html', context = session['context'])
