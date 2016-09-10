from flask import Flask, request, redirect
app = Flask(__name__)

def ssl_enabled(f):
    
    def wrapper(name):
        if request.headers.get('X-Forwarded-Proto') == "http":
            return redirect(request.url.replace('http://', 'https://', 1), code=301)
        else:
            return f(name)
            
    return wrapper

@ssl_enabled
def _hello(name):
    return "Hello {}".format(name)

@app.route('/')
def hello():
    return _hello("World")
    
@app.route('/<name>')
def hello_name(name):
    return _hello(name)

if __name__ == '__main__':
    app.run()
