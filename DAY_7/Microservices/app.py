from flask import Flask, request, jsonify
from models import Item
from pydantic import ValidationError

app = Flask(__name__)

# In-memory "database"
items_db = {}

@app.route("/items", methods=["POST"])
def create_item():
    try:
        # Parse and validate input with Pydantic
        item_data = Item(**request.json)
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    items_db[item_data.id] = item_data.dict()
    return jsonify(items_db[item_data.id]), 201


@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id):
    item = items_db.get(item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404
    return jsonify(item)


@app.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    if item_id not in items_db:
        return jsonify({"error": "Item not found"}), 404
    try:
        updated_item = Item(**request.json)
    except ValidationError as e:
        return jsonify({"errors": e.errors()}), 400

    items_db[item_id] = updated_item.dict()
    return jsonify(items_db[item_id])


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    if item_id not in items_db:
        return jsonify({"error": "Item not found"}), 404
    del items_db[item_id]
    return "", 204


if __name__ == "__main__":
    app.run(debug=True)