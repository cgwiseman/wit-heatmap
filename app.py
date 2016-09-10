from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def hello():
    proto = request.headers.get('X-Forwarded-Proto')
    if proto == "http":
        return redirect(request.url.replace('http://', 'https://', 1), code=301)
    
    return "Hello World!"
    
@app.route('/<name>')
def hello_name(name):
    return "Hello {}!".format(name)

if __name__ == '__main__':
    app.run()
