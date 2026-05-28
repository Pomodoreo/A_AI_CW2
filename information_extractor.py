# information_extractor.py
# Enhanced multi-parameter extraction for accurate information collection
# Works alongside existing NLP without requiring changes to existing code

import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher

# Station dictionary (can be imported from nlp.py)
RAILWAY_STATIONS = {}
try:
    with open("data/uk_railway_stations.txt") as file:
        for line in file:
            parts = line.split(' | ')
            RAILWAY_STATIONS[parts[0].lower().strip()] = parts[1].strip()
except:
    # Fallback if file not found
    RAILWAY_STATIONS = {
        'london': 'LON',
        'manchester': 'MAN',
        'birmingham': 'BHM',
        'southampton': 'SOU',
        'weymouth': 'WEY'
    }


class MultiParamExtractor:
    """
    Improved information extraction that handles multiple parameters in a single input.
    Can extract: ticket type, from_station, to_station, date, time, modifiers
    
    Designed to work with existing NLP pipeline - non-invasive enhancement.
    """
    
    def __init__(self, railway_stations_dict=None):
        self.stations = railway_stations_dict or RAILWAY_STATIONS
        self.ticket_patterns = {
            'one way': [r'\bone\s+way\b', r'\bsingle\b', r'\bone-way\b'],
            'return': [r'\breturn\b', r'\bround\s+trip\b', r'\bround-trip\b'],
            'open ticket': [r'\bopen\s+ticket\b'],
            'open return': [r'\bopen\s+return\b']
        }
        self.time_modifiers = ['before', 'after', 'around', 'early', 'late', 'morning', 'afternoon', 'evening', 'night']
    
    def extract_all(self, user_input, journey_context=None):
        """
        Extract all available information from input in one pass.
        
        Args:
            user_input: User's text input
            journey_context: Existing journey state dict (optional, for contextual extraction)
        
        Returns:
            dict: {
                'ticket': ticket_type or None,
                'from_station': station_name or None,
                'to_station': station_name or None,
                'date': datetime or None,
                'return_date': datetime or None,
                'time': 'HHMM' string or None,
                'return_time': 'HHMM' string or None,
                'time_modifier': 'before'/'after'/etc or None,
                'confidence': float (0-1),
                'extraction_method': str (for debugging)
            }
        """
        journey_context = journey_context or {}
        result = {
            'ticket': None,
            'from_station': None,
            'to_station': None,
            'date': None,
            'return_date': None,
            'time': None,
            'return_time': None,
            'time_modifier': None,
            'confidence': 0.0,
            'extraction_method': []
        }
        
        # Step 1: Extract ticket type (high confidence)
        result['ticket'] = self._extract_ticket(user_input)
        if result['ticket']:
            result['extraction_method'].append('ticket_regex')
        
        # Step 2: Extract stations (high confidence if structured input)
        from_station, to_station, method = self._extract_stations(user_input, journey_context)
        result['from_station'] = from_station
        result['to_station'] = to_station
        if method:
            result['extraction_method'].append(method)
        
        # Step 3: Extract times with modifiers
        time_info = self._extract_times(user_input, result['ticket'])
        result.update(time_info)
        
        # Step 4: Extract dates
        date_info = self._extract_dates(user_input, result['ticket'])
        result.update(date_info)
        
        # Calculate overall confidence
        result['confidence'] = self._calculate_confidence(result)
        
        return result
    
    def _extract_ticket(self, user_input):
        """Extract ticket type with typo tolerance."""
        user_lower = user_input.lower()
        
        # Direct matches (prioritized)
        for ticket_type, patterns in self.ticket_patterns.items():
            for pattern in patterns:
                if re.search(pattern, user_lower, re.IGNORECASE):
                    return ticket_type
        
        # Fuzzy match for typos (e.g., "retrun" → "return")
        ticket_words = [item for items in self.ticket_patterns.values() for item in items]
        for ticket_word in ['one way', 'single', 'return', 'round trip', 'open ticket', 'open return']:
            if self._fuzzy_match(ticket_word, user_lower, threshold=0.75):
                for ticket_type, keywords in self.ticket_patterns.items():
                    if ticket_word in ' '.join(keywords):
                        return ticket_type
        
        return None
    
    def _extract_stations(self, user_input, journey_context):
        """
        Extract from/to stations with structured pattern priority.
        Returns: (from_station, to_station, method_used)
        """
        user_lower = user_input.lower()
        
        # Pattern 1: "from X to Y" or "from X to Y at TIME"
        from_to_match = re.search(
            r'\bfrom\s+([a-z\s]+?)\s+to\s+([a-z\s]+?)(?:\s+at\s+|$|\d{1,2}:|\s+on\s+)',
            user_lower
        )
        if from_to_match:
            from_text = from_to_match.group(1).strip()
            to_text = from_to_match.group(2).strip()
            
            from_station = self._normalize_and_match_station(from_text)
            to_station = self._normalize_and_match_station(to_text)
            
            if from_station and to_station:
                return (from_station, to_station, 'from_to_pattern')
        
        # Pattern 2: "leaving X, arriving Y" or "departing X, getting to Y"
        alt_pattern = re.search(
            r'\b(?:leaving|departing|boarding)\s+(?:from\s+)?([a-z\s]+?)(?:\s*,|\s+(?:arriving|reaching|getting))\s+([a-z\s]+?)(?:$|\s|at\s)',
            user_lower
        )
        if alt_pattern:
            from_text = alt_pattern.group(1).strip()
            to_text = alt_pattern.group(2).strip()
            
            from_station = self._normalize_and_match_station(from_text)
            to_station = self._normalize_and_match_station(to_text)
            
            if from_station and to_station:
                return (from_station, to_station, 'alt_pattern')
        
        # Pattern 3: Single station with context
        single_station_match = re.search(
            r'\b(?:from|to|at|in|going\s+to)\s+([a-z\s]+?)(?:$|\s+at\s+|\s+on\s+|\d{1,2}:)',
            user_lower
        )
        if single_station_match:
            station_text = single_station_match.group(1).strip()
            station = self._normalize_and_match_station(station_text)
            
            if station:
                # Contextually determine if from or to
                if 'from' in user_lower or 'departing' in user_lower or 'leaving' in user_lower:
                    return (station, None, 'single_from_context')
                elif 'to' in user_lower or 'going' in user_lower or 'arriving' in user_lower:
                    return (None, station, 'single_to_context')
        
        return (None, None, None)
    
    def _normalize_and_match_station(self, station_text):
        """Normalize station name and find best match."""
        if not station_text:
            return None
        
        # Clean up
        clean = station_text.strip().lower()
        clean = re.sub(r'\b(station|central|airport|junction|main|terminal)\b', '', clean).strip()
        
        if not clean or len(clean) < 2:
            return None
        
        # Direct code match
        code_to_station = {code.lower(): station for station, code in self.stations.items()}
        if clean in code_to_station:
            return code_to_station[clean]
        
        # Fuzzy match with normalized scores
        best_match = None
        best_score = 0
        
        for station_name in self.stations.keys():
            station_lower = station_name.lower()
            # Remove common suffixes for comparison
            station_compare = re.sub(r'\b(station|central|airport)\b', '', station_lower).strip()
            
            score = SequenceMatcher(None, clean, station_compare).ratio()
            
            # Boost score if clean input is contained in station name
            if clean in station_compare and len(clean) > 3:
                score += 0.20
            
            # Boost score for exact suffix match (e.g., "london" matches "london waterloo")
            if station_compare.endswith(clean) and len(clean) > 2:
                score += 0.15
            
            if score > best_score:
                best_score = score
                best_match = station_name
        
        # Return if confidence is high enough
        if best_score >= 0.72:
            return best_match
        
        return None
    
    def _extract_times(self, user_input, ticket_type):
        """
        Extract departure and return times with modifiers.
        Returns dict with 'time', 'return_time', 'time_modifier'
        """
        user_lower = user_input.lower()
        result = {
            'time': None,
            'return_time': None,
            'time_modifier': None
        }
        
        # Extract time modifier
        for modifier in self.time_modifiers:
            if modifier in user_lower:
                result['time_modifier'] = modifier
                break
        
        # Find all times in input
        times = self._find_all_times(user_input)
        
        if not times:
            return result
        
        if len(times) == 1:
            # Single time - guess if departure or return based on context
            time_str = times[0]
            if 'return' in user_lower or 'back' in user_lower or 'coming back' in user_lower:
                result['return_time'] = time_str
            else:
                result['time'] = time_str
        
        elif len(times) >= 2:
            # Multiple times - assign based on context
            if ticket_type == 'return':
                # First time = departure, second = return
                result['time'] = times[0]
                result['return_time'] = times[1]
            else:
                # Single ticket - use first time, ignore others
                result['time'] = times[0]
        
        return result
    
    def _find_all_times(self, user_input):
        """Find all valid times in input. Returns list of 'HHMM' strings."""
        times = []
        
        # Pattern 1: HH:MM with optional AM/PM
        for match in re.finditer(r'\b(\d{1,2}):(\d{2})\s*(am|pm)?\b', user_input, re.IGNORECASE):
            hours = int(match.group(1))
            minutes = int(match.group(2))
            meridiem = match.group(3)
            
            # Convert to 24-hour if needed
            if meridiem:
                meridiem = meridiem.lower()
                if meridiem == 'pm' and hours != 12:
                    hours += 12
                elif meridiem == 'am' and hours == 12:
                    hours = 0
            
            # Validate
            if 0 <= hours < 24 and 0 <= minutes < 60:
                times.append(f"{hours:02d}{minutes:02d}")
        
        # Pattern 2: HH AM/PM (e.g., "3 pm")
        for match in re.finditer(r'\b(\d{1,2})\s+(am|pm)\b', user_input, re.IGNORECASE):
            hours = int(match.group(1))
            meridiem = match.group(2).lower()
            
            if meridiem == 'pm' and hours != 12:
                hours += 12
            elif meridiem == 'am' and hours == 12:
                hours = 0
            
            if 0 <= hours < 24:
                times.append(f"{hours:02d}00")
        
        # Pattern 3: 4-digit time (e.g., "1430") - with validation
        for match in re.finditer(r'\b(\d{4})\b', user_input):
            time_str = match.group(1)
            hours = int(time_str[:2])
            minutes = int(time_str[2:])
            
            if 0 <= hours < 24 and 0 <= minutes < 60:
                times.append(time_str)
        
        return times
    
    def _extract_dates(self, user_input, ticket_type):
        """
        Extract departure and return dates.
        Returns dict with 'date', 'return_date'
        """
        user_lower = user_input.lower()
        result = {
            'date': None,
            'return_date': None
        }
        
        # Find all date patterns
        dates = self._find_all_dates(user_input)
        
        if not dates:
            return result
        
        if len(dates) == 1:
            date_obj = dates[0]
            if 'return' in user_lower or 'back' in user_lower or 'coming back' in user_lower:
                result['return_date'] = date_obj
            else:
                result['date'] = date_obj
        
        elif len(dates) >= 2:
            # For return tickets, first date is departure, second is return
            result['date'] = dates[0]
            result['return_date'] = dates[1]
        
        return result
    
    def _find_all_dates(self, user_input):
        """Find all valid dates in input. Returns list of datetime objects."""
        dates = []
        
        # Pattern 1: DD/MM/YYYY or DD-MM-YYYY
        for match in re.finditer(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', user_input):
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))
                date_obj = datetime(year, month, day)
                dates.append(date_obj)
            except ValueError:
                pass
        
        # Pattern 2: DD Mon YYYY or DD Mon (e.g., "25 Dec 2024" or "25 December")
        months_abbr = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        months_full = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
        
        for month_name in months_full + months_abbr:
            for match in re.finditer(rf'\b(\d{{1,2}})\s+{month_name}\s*(?:(\d{{4}}))?', user_input, re.IGNORECASE):
                try:
                    day = int(match.group(1))
                    year = int(match.group(2)) if match.group(2) else datetime.now().year
                    month = months_full.index(month_name.lower()) + 1 if month_name.lower() in months_full else months_abbr.index(month_name.lower()) + 1
                    date_obj = datetime(year, month, day)
                    dates.append(date_obj)
                except (ValueError, IndexError):
                    pass
        
        # Pattern 3: "today", "tomorrow", relative dates
        if 'today' in user_input.lower():
            dates.append(datetime.now())
        if 'tomorrow' in user_input.lower() or 'tommorow' in user_input.lower():
            dates.append(datetime.now() + timedelta(days=1))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_dates = []
        for date_obj in dates:
            date_key = date_obj.date()
            if date_key not in seen:
                seen.add(date_key)
                unique_dates.append(date_obj)
        
        return unique_dates
    
    def _fuzzy_match(self, target, text, threshold=0.75):
        """Fuzzy match target string in text."""
        ratio = SequenceMatcher(None, target.lower(), text.lower()).ratio()
        return ratio >= threshold
    
    def _calculate_confidence(self, result):
        """Calculate overall extraction confidence (0-1)."""
        confidence = 0.0
        weight_sum = 0.0
        
        # Ticket type: high confidence if found
        if result['ticket']:
            confidence += 0.25
        weight_sum += 0.25
        
        # Stations: high confidence if both from and to found
        if result['from_station'] and result['to_station']:
            confidence += 0.35
        elif result['from_station'] or result['to_station']:
            confidence += 0.15
        weight_sum += 0.35
        
        # Date: medium confidence
        if result['date']:
            confidence += 0.20
        weight_sum += 0.20
        
        # Time: medium confidence
        if result['time']:
            confidence += 0.15
        weight_sum += 0.15
        
        # Return date/time: low confidence if ticket is return
        if result['return_date'] or result['return_time']:
            confidence += 0.05
        weight_sum += 0.05
        
        return min(confidence / weight_sum, 1.0) if weight_sum > 0 else 0.0


# Convenience function for one-off extraction
def extract_all_info(user_input, journey_context=None):
    """Quick function to extract all information from user input."""
    extractor = MultiParamExtractor()
    return extractor.extract_all(user_input, journey_context)
