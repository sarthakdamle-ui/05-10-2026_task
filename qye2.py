cost_price = int(input())
selling_price = int(input())
                    
if selling_price > cost_price:
    print("Profit =", selling_price - cost_price)
else:
    print("Loss =", cost_price - selling_price)