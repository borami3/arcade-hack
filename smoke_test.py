"""One end-to-end Arcade call: create -> poll -> product. Prints raw JSON so we can see the shapes."""
import json

import arcade

arcade.load_env()
cats = arcade.jewelry_categories()
cat = cats["Pendant Necklace"]
job = arcade.create_pattern(
    "A delicate 14k gold vermeil pendant necklace shaped like a small olive leaf sprig, garden wedding, minimalist",
    cat["categoryId"],
)
print("create:", json.dumps(job, indent=2))
job = arcade.wait_for_job(job["jobId"])
print("job:", json.dumps(job, indent=2))
if job["status"] == "succeeded":
    print("product:", json.dumps(arcade.get_product(job["result"]["productId"]), indent=2))
