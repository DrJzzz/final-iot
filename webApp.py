from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/sensor-data', methods=['POST'])
def receive_sensor_data():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid data format"}), 400
    
    return jsonify({"status": "ok"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
