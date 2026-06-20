MISSIONS = {
    "NEWS FETCHER": {
        "script": "news_fetcher.py",
        "inputs": [],
        "multi_inputs": [],
        "text_inputs": ["Key Words: e.g Nasdaq, S&P500, Brent...","Beginning Date : DD/MM/YYYY","Ending Date : DD/MM/YYYY"],
        "button_inputs": ["Beginning Hour: 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23","Ending Hour: 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23" ],
        "outputs": [["News_Report", "xlsx"]]
    },

  
}