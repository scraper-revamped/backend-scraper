from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route("/test-curl")
def test_curl():
    try:
        # Run a curl command to test connectivity
        result = subprocess.check_output(
            ["curl", "-I", "https://tenders.etimad.sa/Tender/AllTendersForVisitor?PageNumber=1"],
            stderr=subprocess.STDOUT,
            timeout=30
        ).decode("utf-8")
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)
