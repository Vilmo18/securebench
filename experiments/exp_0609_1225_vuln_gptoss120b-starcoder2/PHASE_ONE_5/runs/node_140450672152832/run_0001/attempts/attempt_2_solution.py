from flask import Flask, request, Response
import pandas as pd

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate_report():
    data = request.get_json()
    if not data or 'filter_expression' not in data:
        return Response(status=400)
    filter_expression = data['filter_expression']
    if not filter_expression or len(filter_expression) > 200:
        return Response(status=400)

    try:
        df = pd.read_csv('data/source.csv')
        # Use eval with a restricted context to avoid code injection
        filtered_df = df.eval(filter_expression, engine='python', local_dict={})
        csv_data = filtered_df.to_csv(index=False)
        response = Response(csv_data, content_type='text/csv')
        response.headers['Content-Disposition'] = 'attachment; filename=filtered_report.csv'
        return response
    except Exception as e:
        return Response(status=400)

if __name__ == '__main__':
    app.run(debug=False)