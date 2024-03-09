import plotly.graph_objs as go
import plotly.offline as opy


def get_prediction_distribution_chart(prediction_counts):
    labels = list(prediction_counts.keys())
    values = list(prediction_counts.values())

    data = [go.Bar(x=labels, y=values)]
    layout = go.Layout(title='Prediction Distribution', xaxis=dict(title='Prediction'), yaxis=dict(title='Count'))
    fig = go.Figure(data=data, layout=layout)

    return opy.plot(fig, auto_open=False, output_type='div')
