"""
Test script to verify gorilla variant spawn probabilities
"""
import random
import config

def choose_variant():
    """
    Choose a gorilla variant based on configured weights.
    (Copied from gorilla.py _choose_variant method)
    """
    variants = getattr(config, "GORILLA_VARIANTS", {})
    if not variants:
        return "default", config.GORILLA_STATS

    names = list(variants.keys())
    weights = [variants[n].get("weight", 1.0) for n in names]
    total = sum(weights)
    pick = random.uniform(0, total)
    accum = 0.0
    for name, w in zip(names, weights):
        accum += w
        if pick <= accum:
            return name, variants[name]
    return names[-1], variants[names[-1]]

def test_spawn_probabilities(num_trials=10000):
    """
    Test gorilla variant spawn probabilities over many trials
    """
    print(f"Testing gorilla variant spawn probabilities ({num_trials:,} trials)...\n")

    # Count spawns
    spawn_counts = {}
    for _ in range(num_trials):
        variant_name, variant_data = choose_variant()
        spawn_counts[variant_name] = spawn_counts.get(variant_name, 0) + 1

    # Calculate and display results
    print("Expected vs Actual spawn rates:")
    print("-" * 60)
    print(f"{'Type':<10} {'Expected %':<12} {'Actual %':<12} {'Count':<10}")
    print("-" * 60)

    for variant_name in config.GORILLA_VARIANTS.keys():
        expected_weight = config.GORILLA_VARIANTS[variant_name]["weight"]
        total_weight = sum(v["weight"] for v in config.GORILLA_VARIANTS.values())
        expected_pct = (expected_weight / total_weight) * 100

        actual_count = spawn_counts.get(variant_name, 0)
        actual_pct = (actual_count / num_trials) * 100

        print(f"{variant_name:<10} {expected_pct:>10.2f}% {actual_pct:>10.2f}% {actual_count:>8,}")

    print("-" * 60)
    print("\nVariant Stats Summary:")
    print("-" * 80)
    print(f"{'Type':<10} {'HP':<8} {'Speed':<7} {'Attack':<8} {'Atk/Sec':<10} {'Knockback':<10}")
    print("-" * 80)

    for variant_name, variant_data in config.GORILLA_VARIANTS.items():
        hp = variant_data["hp"]
        speed = variant_data["speed"]
        attack = variant_data["attack"]
        atk_speed = variant_data["attack_speed"] / 10  # Convert to attacks per second
        knockback = variant_data["knockback_distance"]

        print(f"{variant_name:<10} {hp:<8,} {speed:<7} {attack:<8} {atk_speed:<10.1f} {knockback:<10}")

    print("-" * 80)

if __name__ == "__main__":
    test_spawn_probabilities()
