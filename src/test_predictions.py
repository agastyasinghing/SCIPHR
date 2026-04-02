"""
Test predictions on specific fights
"""

from src.predictor import UFCFightPredictor

# Initialize predictor
predictor = UFCFightPredictor()

print("\n" + "="*70)
print("TESTING MODEL ON 3 FIGHTS")
print("="*70)

# Fight 1: Upcoming main event
print("\n\n" + "🔴 FIGHT 1: UPCOMING MAIN EVENT")
print("-"*70)
result1 = predictor.predict_fight("Islam Makhachev", "JDM")

# Fight 2: Topuria domination
print("\n\n" + "🔴 FIGHT 2: TOPURIA DOMINATION (Topuria won)")
print("-"*70)
result2 = predictor.predict_fight("Ilia Topuria", "Charles Oliveira")

# Fight 3: Close fight with comeback
print("\n\n" + "🔴 FIGHT 3: CLOSE FIGHT (Jiri won via KO R3)")
print("-"*70)
result3 = predictor.predict_fight("Jiri Prochazka", "Khalil Rountree")

# Summary
print("\n\n" + "="*70)
print("SUMMARY OF PREDICTIONS")
print("="*70)

fights = [
    ("Islam Makhachev vs JDM", result1, "Upcoming"),
    ("Ilia Topuria vs Charles Oliveira", result2, "Topuria won"),
    ("Jiri Prochazka vs Khalil Rountree", result3, "Jiri won R3 KO")
]

for fight_name, result, actual in fights:
    if result:
        correct = "✓" if actual == "Upcoming" or result['winner'] in actual else "✗"
        print(f"\n{fight_name}")
        print(f"  Prediction: {result['winner']} ({result['confidence']:.1%})")
        print(f"  Actual: {actual}")
        if correct == "✓" and actual != "Upcoming":
            print(f"  {correct} CORRECT")
        elif actual != "Upcoming":
            print(f"  {correct} INCORRECT")