from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods = ['POST', 'GET'])
def hello():
   if request.method == 'POST':
      text = request.form.get('text')
      return render_template('index.html', text=text)
   return render_template('index.html', problem_txt="Hello Paul")
