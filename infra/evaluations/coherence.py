import json
import prompty
from pathlib import Path

# run a batch coherence evaluation
@prompty.trace
def batch(file):
    with open(file) as f:
        data = f.readlines()

    results = []
    for lines in data:
        data = json.loads(lines)
        result = evaluate(data["question"], data["context"], data["answer"])
        results.append(result)

    return results


# run a single coherence evaluation
@prompty.trace
def evaluate(question, context, answer):
    return prompty.execute("coherence.prompty", inputs={
        "question": question,
        "context": context,
        "answer": answer
    })


if __name__ == "__main__":
    question = "What feeds all the fixtures in low voltage tracks instead of each light having a line-to-low voltage transformer?"
    context = "Track lighting, invented by Lightolier, was popular at one period of time because it was much easier to install than recessed lighting, and individual fixtures are decorative and can be easily aimed at a wall. It has regained some popularity recently in low-voltage tracks, which often look nothing like their predecessors because they do not have the safety issues that line-voltage systems have, and are therefore less bulky and more ornamental in themselves. A master transformer feeds all of the fixtures on the track or rod with 12 or 24 volts, instead of each light fixture having its own line-to-low voltage transformer. There are traditional spots and floods, as well as other small hanging fixtures. A modified version of this is cable lighting, where lights are hung from or clipped to bare metal cables under tension"
    answer = "The main transformer is the object that feeds all the fixtures in low voltage tracks."
    eval = evaluate(question, context, answer)
    print(eval)

    data = Path.joinpath(Path(__file__).parent, "data.jsonl")
    batch_eval = batch(data)
    print(batch_eval)
