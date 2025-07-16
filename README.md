AI Physics Tutor using vector embeddings to compare student responses to model responses stored in a json file.
Uses sympy for equation comparison.
Web-based interface with flask for backend.

backend flask file: vector_dialog_flask.py
NLP:                ml.py
Ramp test:          ramp.json
html:               index.html

Use this embedding model via ollama:
https://ollama.com/blog/embedding-models
https://huggingface.co/CompendiumLabs/bge-base-en-v1.5-gguf
hf.co/CompendiumLabs/bge-base-en-v1.5-gguf

To run:
export FLASK_APP=vector_dialog_flask
flask --debug run


