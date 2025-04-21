from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from database.symbol import enhanced_search_symbols
from utils.session import check_session_validity
from typing import List, Dict
import logging
from strategies.chatgpt.watchlist import load_watchlist, save_watchlist

logger = logging.getLogger(__name__)

search_bp = Blueprint('search_bp', __name__, url_prefix='/search')

@search_bp.route('/token')
@check_session_validity
def token():
    """Route for the search form page"""
    return render_template('token.html')

@search_bp.route('/')
@check_session_validity
def search():
    """Main search route for full results page"""
    query = request.args.get('symbol', '').strip()
    exchange = request.args.get('exchange')
    from strategies.chatgpt.watchlist import load_watchlist
    
    if not query:
        logger.info("Empty search query received")
        flash('Please enter a search term.', 'error')
        return render_template('token.html')
    
    logger.info(f"Searching for symbol: {query}, exchange: {exchange}")
    results = enhanced_search_symbols(query, exchange)
    
    if not results:
        logger.info(f"No results found for query: {query}")
        flash('No matching symbols found.', 'error')
        return render_template('token.html')
    
    results_dicts = [{
        'symbol': result.symbol,
        'brsymbol': result.brsymbol,
        'name': result.name,
        'exchange': result.exchange,
        'brexchange': result.brexchange,
        'token': result.token,
        'expiry': result.expiry,
        'strike': result.strike,
        'lotsize': result.lotsize,
        'instrumenttype': result.instrumenttype,
        'tick_size': result.tick_size
    } for result in results]
    
    # Load current watchlist for pre-disabling
    watchlist = load_watchlist()
    watchlist_set = set((s['symbol'], s['exchange']) for s in watchlist)
    
    logger.info(f"Found {len(results_dicts)} results for query: {query}")
    return render_template('search.html', results=results_dicts, watchlist_set=watchlist_set)

@search_bp.route('/api/search')
@check_session_validity
def api_search():
    """API endpoint for AJAX search suggestions"""
    query = request.args.get('q', '').strip()
    exchange = request.args.get('exchange')
    
    if not query:
        logger.debug("Empty API search query received")
        return jsonify({'results': []})
    
    logger.debug(f"API search for symbol: {query}, exchange: {exchange}")
    results = enhanced_search_symbols(query, exchange)
    results_dicts = [{
        'symbol': result.symbol,
        'brsymbol': result.brsymbol,
        'name': result.name,
        'exchange': result.exchange,
        'token': result.token
    } for result in results]
    
    logger.debug(f"API search found {len(results_dicts)} results")
    return jsonify({'results': results_dicts})

@search_bp.route('/api/watchlist/add', methods=['POST'])
def api_add_to_watchlist():
    """API endpoint to add a stock to the watchlist.json file (only symbol & exchange)"""
    if not request.is_json:
        return jsonify(success=False, error="Invalid request format (expected JSON)"), 400
    stock = request.get_json()
    # Only keep 'symbol' and 'exchange' fields
    minimal_stock = {
        'symbol': stock.get('symbol'),
        'exchange': stock.get('exchange')
    }
    if not minimal_stock['symbol'] or not minimal_stock['exchange']:
        return jsonify(success=False, error="Missing symbol or exchange"), 400
    try:
        current = load_watchlist()
        if any(s.get('symbol') == minimal_stock['symbol'] and s.get('exchange') == minimal_stock['exchange'] for s in current):
            return jsonify(success=True, message="Already in watchlist")
        current.append(minimal_stock)
        if save_watchlist(current):
            return jsonify(success=True)
        else:
            return jsonify(success=False, error="Failed to save watchlist"), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

@search_bp.route('/watchlist')
@check_session_validity
def watchlist_page():
    watchlist = load_watchlist()
    return render_template('watchlist.html', watchlist=watchlist)

@search_bp.route('/watchlist/api/remove', methods=['POST'])
@check_session_validity
def api_remove_from_watchlist():
    if not request.is_json:
        return jsonify(success=False, error="Invalid request format (expected JSON)"), 400
    data = request.get_json()
    symbol = data.get('symbol')
    exchange = data.get('exchange')
    if not symbol or not exchange:
        return jsonify(success=False, error="Missing symbol or exchange"), 400
    try:
        current = load_watchlist()
        new_watchlist = [s for s in current if not (s.get('symbol') == symbol and s.get('exchange') == exchange)]
        if len(new_watchlist) == len(current):
            return jsonify(success=False, error="Stock not found in watchlist"), 404
        if save_watchlist(new_watchlist):
            return jsonify(success=True)
        else:
            return jsonify(success=False, error="Failed to save watchlist"), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
