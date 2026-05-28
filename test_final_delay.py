#!/usr/bin/env python3
"""Test the new delay_handler_final with exit commands and enhanced model."""

import sys
sys.path.insert(0, r'C:\Users\comet\OneDrive\Documents\A_AI_CW2')

from delay_handler_final import (
    DelaySession, handle_delay_input, start_delay_prediction,
    check_exit_command, format_time_display, minutes_to_time,
    extract_multiple_params
)


def test_exit_command():
    """Test that exit commands work properly."""
    print("Testing exit commands...")
    
    exit_words = ['exit', 'quit', 'done', 'back', 'cancel', 'stop', 'end', 'leave']
    for word in exit_words:
        result = check_exit_command(word)
        assert result == True, f"Failed to recognize '{word}' as exit command"
        print(f"  ✓ '{word}' recognized as exit")
    
    non_exit = ['help', 'hello', 'next', 'continue']
    for word in non_exit:
        result = check_exit_command(word)
        assert result == False, f"Incorrectly recognized '{word}' as exit command"
        print(f"  ✓ '{word}' NOT recognized as exit")
    
    print("Exit command tests: PASSED\n")


def test_midnight_boundary():
    """Test time calculations across midnight boundary."""
    print("Testing midnight boundary handling...")
    
    # Test case 1: 23:44 with 12 minute delay = 00:28 (next day wrap)
    result = minutes_to_time(23*60 + 44 + 44)  # 1424 + 44 = 1468 % 1440 = 28
    expected = "00:28"
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"  ✓ 23:44 + 44min = {result} (crosses midnight)")
    
    # Test case 2: 23:00 with 60 minute delay = 00:00
    result = minutes_to_time(23*60 + 60)  # 1380 + 60 = 1440 % 1440 = 0
    expected = "00:00"
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"  ✓ 23:00 + 60min = {result} (midnight)")
    
    # Test case 3: Normal time within day
    result = minutes_to_time(15*60 + 30)  # 930 minutes = 15:30
    expected = "15:30"
    assert result == expected, f"Expected {expected}, got {result}"
    print(f"  ✓ 15:30 stays 15:30 (no boundary)")
    
    print("Midnight boundary tests: PASSED\n")


def test_session_flexibility():
    """Test that session accepts parameters in any order."""
    print("Testing flexible parameter input...")
    
    session = DelaySession()
    
    # Provide parameters out of order
    test_inputs = [
        "delayed 12 minutes",
        "Southampton",
        "16:30",
        "to London Waterloo"
    ]
    
    for inp in test_inputs:
        status, response = handle_delay_input(inp, session)
        print(f"  Input: '{inp}'")
        print(f"    Status: {status}, Session complete: {session.is_complete()}\n")
    
    # Check if all parameters were captured
    assert session.from_station_code == 'SOU', f"Expected SOU, got {session.from_station_code}"
    assert session.to_station_code == 'WAT', f"Expected WAT, got {session.to_station_code}"
    assert session.planned_arrival_time == '1630', f"Expected 1630, got {session.planned_arrival_time}"
    assert session.current_delay == 12, f"Expected 12, got {session.current_delay}"
    
    print("Flexible input tests: PASSED\n")


def test_delay_time_string_format():
    """Test that hh:mm delay values are parsed as minutes."""
    print("Testing hh:mm delay parsing...")

    session = DelaySession()
    extracted = extract_multiple_params(
        "from Southampton to London Waterloo at 23:54 delayed 00:12",
        session
    )
    assert extracted['time'] == '2354', f"Expected planned arrival time 2354, got {extracted['time']}"
    assert extracted['delay'] == 12, f"Expected delay 12, got {extracted['delay']}"
    assert extracted['from_station'][1] == 'SOU', f"Expected from SOU, got {extracted['from_station'][1]}"
    assert extracted['to_station'][1] == 'WAT', f"Expected to WAT, got {extracted['to_station'][1]}"
    print("  ✓ hh:mm delay value parsed correctly")
    print("hh:mm delay parsing tests: PASSED\n")


def test_multi_piece_flexible_input():
    """Test that multiple journey pieces can arrive in one utterance."""
    print("Testing flexible multi-piece input...")

    session = DelaySession()
    status, response = handle_delay_input(
        "Southampton Waterloo at 23:54 delayed 00:12",
        session
    )

    assert session.from_station_code == 'SOU', f"Expected SOU, got {session.from_station_code}"
    assert session.to_station_code == 'WAT', f"Expected WAT, got {session.to_station_code}"
    assert session.planned_arrival_time == '2354', f"Expected 2354, got {session.planned_arrival_time}"
    assert session.current_delay == 12, f"Expected 12, got {session.current_delay}"
    assert status == 'PREDICTION', f"Expected PREDICTION, got {status}"
    print("  ✓ multi-piece input extracted all fields")
    print("Flexible multi-piece input tests: PASSED\n")


def test_exit_clears_session():
    """Test that exit command properly exits delay mode."""
    print("Testing exit command flow...")
    
    session = DelaySession()
    
    # Add some data
    session.from_station = "Southampton Central"
    session.from_station_code = "SOU"
    
    # Try to exit
    status, response = handle_delay_input("exit", session)
    assert status == "EXIT_DELAY_MODE", f"Expected EXIT_DELAY_MODE, got {status}"
    print(f"  ✓ Exit detected correctly")
    print(f"    Response: {response}\n")
    
    print("Exit flow tests: PASSED\n")


def test_no_emojis():
    """Verify no emojis in output."""
    print("Testing that output has no emojis...")
    
    greeting = start_delay_prediction()
    
    emoji_chars = ['🚂', '🚁', '⏰', '⚠️', '📍', '📊', '✅', '❌', 'ℹ️', '💡', '🎯', '📝']
    
    for emoji in emoji_chars:
        assert emoji not in greeting, f"Found emoji {emoji} in greeting"
    
    assert emoji not in greeting, "Found emoji in greeting"
    print(f"  ✓ Greeting has no emojis")
    
    # Check other outputs
    session = DelaySession()
    status, response = handle_delay_input("Southampton", session)
    
    for emoji in emoji_chars:
        assert emoji not in response, f"Found emoji {emoji} in response"
    
    print(f"  ✓ Response has no emojis\n")
    
    print("No emoji tests: PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing delay_handler_final improvements")
    print("=" * 60 + "\n")
    
    try:
        test_exit_command()
        test_midnight_boundary()
        test_session_flexibility()
        test_delay_time_string_format()
        test_multi_piece_flexible_input()
        test_exit_clears_session()
        test_no_emojis()
        
        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
