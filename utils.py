#
# utils.py
#
# This file holds all your business logic and calculations,
# keeping your app.py clean and focused on routes.
#

def process_portfolio_data(all_stocks):
    """
    Takes a list of Stock objects from the database and returns
    a formatted portfolio list and a summary dictionary.
    """
    
    portfolio = []
    total_investment = 0
    total_current_value = 0
    
    for stock in all_stocks:
        # 1. Calculate P/L for this one stock
        profit_loss = (stock.current_price - stock.buy_price) * stock.quantity
        
        # 2. Format the stock data as a dictionary (to match index.html)
        stock_data = {
            'id': stock.id,
            'stock_name': stock.stock_name,
            'quantity': stock.quantity,
            'buy_price': round(stock.buy_price, 2),
            'current_price': round(stock.current_price, 2),
            'profit_loss': round(profit_loss, 2)
        }
        
        # 3. Add to our totals
        total_investment += stock.quantity * stock.buy_price
        total_current_value += stock.quantity * stock.current_price
        
        # 4. Add the formatted stock to our portfolio list
        portfolio.append(stock_data)

    # 5. Calculate final summary
    total_profit_loss = total_current_value - total_investment
    
    summary = {
        'total_investment': round(total_investment, 2),
        'total_current_value': round(total_current_value, 2),
        'total_profit_loss': round(total_profit_loss, 2)
    }
    
    # 6. Return both the list and the summary, just as app.py expects
    return portfolio, summary


def calculate_shares_to_buy(q1, p1, p2, p_target):
    """
    Calculates the number of shares (q2) to buy at p2
    to reach a new average price of p_target.
    
    This function is ready for you when you want to add the
    "break-even" feature to your frontend.
    """
    
    # --- Input Validation (Critical) ---
    if p_target <= p2:
        # Impossible: You can't average down to a price
        # at or below the current market price
        return None 
        
    if p_target >= p1:
        # Makes no sense: The target is higher than or equal to
        # your current average. You're not averaging "down".
        return None

    # --- Formula ---
    try:
        numerator = q1 * (p1 - p_target)
        denominator = p_target - p2
        
        q2 = numerator / denominator
        return q2
        
    except Exception as e:
        print(f"Error in calculation: {e}")
        return None