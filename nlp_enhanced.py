# nlp_enhanced.py
# Optional enhancement layer for NLP extraction
# Works alongside existing nlp.py without modification
# Can be gradually adopted throughout the codebase

from information_extractor import extract_all_info
import nlp
from datetime import datetime


def extract_comprehensively(user_input, journey=None):
    """
    Comprehensively extract all available information from user input.
    
    Falls back to original NLP functions if enhanced extraction confidence is low.
    This provides a smooth migration path from existing extraction to improved version.
    
    Args:
        user_input: User's text input
        journey: Existing journey state (optional)
    
    Returns:
        dict with keys: ticket, dest_info, date_info, time_info, confidence, method
    
    Example:
        extraction = extract_comprehensively("return ticket from london to manchester on 25 dec")
        if extraction['confidence'] > 0.7:
            apply_extraction_results(extraction)
        else:
            ask_for_clarification(extraction)
    """
    journey = journey or {}
    
    # Attempt comprehensive extraction
    enhanced = extract_all_info(user_input, journey)
    
    # Determine if enhanced results are reliable enough to use
    confidence_threshold = 0.65  # Can be tuned
    use_enhanced = enhanced['confidence'] >= confidence_threshold
    
    if use_enhanced:
        # High confidence - use enhanced extraction
        result = {
            'confidence': enhanced['confidence'],
            'method': 'enhanced',
            'ticket': enhanced['ticket'] or nlp.check_ticket(user_input),
            'dest_info': {
                'from': enhanced['from_station'],
                'to': enhanced['to_station'],
                'from_options': None,
                'to_options': None
            },
            'date_info': {
                'from': enhanced['date'],
                'to': enhanced['return_date']
            },
            'time_info': {
                'time': enhanced['time'],
                'return_time': enhanced['return_time']
            }
        }
    else:
        # Low confidence or empty result - use original extraction functions
        result = {
            'confidence': 0.0,
            'method': 'original',
            'ticket': nlp.check_ticket(user_input),
            'dest_info': nlp.extract_destination_info(user_input, journey),
            'date_info': nlp.extract_date_info(user_input, journey),
            'time_info': nlp.extract_time_info(user_input, journey)
        }
    
    return result


def should_ask_for_clarification(extraction):
    """
    Determine if system should ask user for clarification based on extraction confidence.
    
    Returns:
        (should_clarify: bool, fields_to_clarify: list)
    
    Example:
        should_clarify, fields = should_ask_for_clarification(extraction)
        if should_clarify:
            bot_message = f"Just to confirm, you want to travel to {fields[0]}?"
    """
    confidence = extraction.get('confidence', 0.0)
    
    # If enhanced extraction with medium confidence, ask for verification
    if extraction.get('method') == 'enhanced' and 0.5 <= confidence < 0.8:
        unclear_fields = []
        
        dest_info = extraction.get('dest_info', {})
        if not dest_info.get('from') or not dest_info.get('to'):
            unclear_fields.append('stations')
        
        date_info = extraction.get('date_info', {})
        if not date_info.get('from'):
            unclear_fields.append('date')
        
        time_info = extraction.get('time_info', {})
        if not time_info.get('time'):
            unclear_fields.append('time')
        
        return True, unclear_fields
    
    # High confidence enhanced extraction
    if extraction.get('method') == 'enhanced' and confidence >= 0.8:
        return False, []
    
    # Original extraction - don't ask for clarification (preserve existing behavior)
    return False, []


def apply_extraction_to_journey(extraction, journey):
    """
    Apply extraction results to journey state.
    Same logic as in main.py, but extracted for reusability.
    
    Args:
        extraction: Result from extract_comprehensively()
        journey: Journey dict to update
    
    Returns:
        Updated journey dict
    """
    # Ticket type
    if extraction.get('ticket'):
        journey['ticket_type'] = extraction['ticket']
    
    # Destination info
    dest_info = extraction.get('dest_info', {})
    if dest_info.get('from'):
        journey['from'] = dest_info['from']
        journey['from_options'] = None
    elif dest_info.get('from_options'):
        journey['from_options'] = dest_info['from_options']
    
    if dest_info.get('to'):
        journey['to'] = dest_info['to']
        journey['to_options'] = None
    elif dest_info.get('to_options'):
        journey['to_options'] = dest_info['to_options']
    
    # Date info
    date_info = extraction.get('date_info', {})
    if date_info.get('from') is not None:
        journey['date'] = date_info['from']
    
    if date_info.get('to') is not None:
        journey['return_date'] = date_info['to']
    
    # Time info
    time_info = extraction.get('time_info', {})
    if time_info.get('time') is not None:
        journey['time'] = time_info['time']
    
    if time_info.get('return_time') is not None:
        journey['return_time'] = time_info['return_time']
    
    return journey


def extract_and_apply(user_input, journey):
    """
    Convenience function: Extract from input and immediately apply to journey.
    
    Args:
        user_input: User's text input
        journey: Existing journey state
    
    Returns:
        tuple: (updated_journey, extraction_result)
    
    Example:
        journey, result = extract_and_apply(user_input, journey)
        response = get_response(journey)
    """
    extraction = extract_comprehensively(user_input, journey)
    journey = apply_extraction_to_journey(extraction, journey)
    return journey, extraction


# ============================================================================
# OPTIONAL: Drop-in replacement for existing extraction in main.py
# ============================================================================

def process_input_enhanced(user_input, journey):
    """
    Enhanced version of main.py's process_input extraction logic.
    
    Drop-in replacement that maintains backward compatibility while improving accuracy.
    
    This can replace lines 507-510 in main.py:
        # Old:
        ticket = check_ticket(user_input)
        dest_info = extract_destination_info(user_input, journey)
        date_info = extract_date_info(user_input, journey)
        time_info = extract_time_info(user_input, journey)
        
        # New:
        ticket, dest_info, date_info, time_info = process_input_enhanced(user_input, journey)
    """
    extraction = extract_comprehensively(user_input, journey)
    
    return (
        extraction.get('ticket'),
        extraction.get('dest_info'),
        extraction.get('date_info'),
        extraction.get('time_info')
    )


# ============================================================================
# Integration with Delay Handler
# ============================================================================

def extract_delay_parameters(user_input):
    """
    Extract delay-specific parameters from user input.
    Can enhance delay_handler_final.py's multi-parameter extraction.
    
    Returns:
        dict with delay-relevant fields
    """
    enhanced = extract_all_info(user_input)
    
    return {
        'from_station': enhanced.get('from_station'),
        'to_station': enhanced.get('to_station'),
        'time': enhanced.get('time'),
        'date': enhanced.get('date'),
        'time_modifier': enhanced.get('time_modifier'),
        'confidence': enhanced.get('confidence'),
        'extraction_method': enhanced.get('extraction_method')
    }


# ============================================================================
# Debugging & Analytics
# ============================================================================

def analyze_extraction_performance(test_inputs):
    """
    Analyze extraction performance on a batch of test inputs.
    Useful for tuning thresholds and confidence scores.
    
    Args:
        test_inputs: List of user input strings
    
    Returns:
        dict with performance metrics
    """
    results = []
    total_confidence = 0.0
    method_counts = {'enhanced': 0, 'original': 0}
    
    for user_input in test_inputs:
        extraction = extract_comprehensively(user_input)
        results.append(extraction)
        total_confidence += extraction.get('confidence', 0.0)
        method_counts[extraction.get('method', 'original')] += 1
    
    avg_confidence = total_confidence / len(test_inputs) if test_inputs else 0.0
    
    return {
        'test_count': len(test_inputs),
        'average_confidence': avg_confidence,
        'enhanced_extractions': method_counts['enhanced'],
        'original_extractions': method_counts['original'],
        'results': results
    }


def print_extraction_analysis(extraction):
    """Pretty-print extraction results for debugging."""
    print("\n" + "=" * 60)
    print("EXTRACTION ANALYSIS")
    print("=" * 60)
    print(f"Confidence: {extraction.get('confidence', 0.0):.2f}")
    print(f"Method: {extraction.get('method', 'unknown')}")
    print(f"\nTicket: {extraction.get('ticket', 'None')}")
    
    dest_info = extraction.get('dest_info', {})
    print(f"From: {dest_info.get('from', 'None')}")
    print(f"To: {dest_info.get('to', 'None')}")
    
    date_info = extraction.get('date_info', {})
    print(f"Date: {date_info.get('from', 'None')}")
    print(f"Return Date: {date_info.get('to', 'None')}")
    
    time_info = extraction.get('time_info', {})
    print(f"Time: {time_info.get('time', 'None')}")
    print(f"Return Time: {time_info.get('return_time', 'None')}")
    print("=" * 60 + "\n")
