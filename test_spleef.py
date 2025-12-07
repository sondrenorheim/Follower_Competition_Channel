"""
Quick test script for Spleef game mode
Tests basic functionality without running full game
"""

import sys
import os

# Fix Windows console encoding
if os.name == 'nt':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

# Import config to set test mode
import config
config.TEST_MODE = True
config.EXPORT_VIDEO = False
config.FOLLOWER_COUNT = 50  # Small test with 50 players

print("=" * 60)
print("SPLEEF TEST - Quick Functionality Check")
print("=" * 60)

# Test imports
print("\n1. Testing imports...")
try:
    from spleef import SpleefGame
    from spleef.arena import SpleefArena
    from spleef.player import SpleefPlayer
    from spleef.block import Block, BlockState
    from spleef.physics import SpleefPhysics
    from spleef.ai import SpleefAI
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test arena creation
print("\n2. Testing arena creation...")
try:
    arena = SpleefArena(center_x=270, top_y=200)
    print(f"✅ Arena created: {arena}")
    print(f"   Layers: {len(arena.layers)}")
    print(f"   Total blocks: {arena.get_total_blocks()}")
    print(f"   Solid blocks: {arena.get_total_solid_blocks()}")
except Exception as e:
    print(f"❌ Arena creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test block degradation
print("\n3. Testing block degradation...")
try:
    block = Block(5, 5)
    print(f"   Initial state: {block.state.name}")
    block.step_on()
    print(f"   After step_on: {block.state.name}")
    print("✅ Block degradation works")
except Exception as e:
    print(f"❌ Block degradation failed: {e}")
    sys.exit(1)

# Test physics system
print("\n4. Testing physics system...")
try:
    physics = SpleefPhysics()
    print(f"✅ Physics initialized: {physics}")
except Exception as e:
    print(f"❌ Physics failed: {e}")
    sys.exit(1)

# Test AI system
print("\n5. Testing AI system...")
try:
    ai = SpleefAI()
    print(f"✅ AI initialized: {ai}")
except Exception as e:
    print(f"❌ AI failed: {e}")
    sys.exit(1)

# Test player creation
print("\n6. Testing player creation...")
try:
    player = SpleefPlayer("testuser", "Test Player", None)
    player.set_spawn_position(100, 200, 0)
    print(f"✅ Player created: {player}")
    print(f"   Position: ({player.x}, {player.y})")
    print(f"   Layer: {player.current_layer}")
except Exception as e:
    print(f"❌ Player creation failed: {e}")
    sys.exit(1)

# Test spawn position generation
print("\n7. Testing spawn position generation...")
try:
    spawn_positions = arena.get_spawn_positions(50)
    print(f"✅ Generated {len(spawn_positions)} spawn positions")
    print(f"   First spawn: {spawn_positions[0]}")
    print(f"   Last spawn: {spawn_positions[-1]}")
except Exception as e:
    print(f"❌ Spawn generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test renderer (without pygame display)
print("\n8. Testing renderer...")
try:
    from spleef.renderer import SpleefRenderer
    renderer = SpleefRenderer(540, 960)
    print(f"✅ Renderer created: {renderer}")
except Exception as e:
    print(f"❌ Renderer failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
print("\nSpleef game mode is ready to run.")
print("To test with full game loop, run:")
print("  python main.py")
print("And set GAME_MODE = 'spleef' in config.py")
