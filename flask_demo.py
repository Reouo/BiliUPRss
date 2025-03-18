from flask import Flask

app = Flask(__name__, static_folder='xml_files')


@app.route('/rss/<path:filename>')
def serve_static(filename):
    return app.send_static_file(filename)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
