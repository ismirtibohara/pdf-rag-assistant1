from src.llm import generate_answer

chunks = [{
    "page": 3, "chunk": 1, "distance": 0.3,
    "text": "Photosynthesis takes place in the chloroplasts of plant cells. "
            "It converts light energy into chemical energy.",
}]

for q in ["Where does photosynthesis take place?", "Who won the 2018 World Cup?"]:
    print("Q:", q)
    print(generate_answer(q, chunks).model_dump_json(indent=2))
    print()