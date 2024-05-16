from flask import Flask, request, render_template, redirect, url_for, flash
import xarray as xr
import numpy as np
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def mean_absolute_error(obs, model):
    return np.mean(np.abs(obs - model))

def root_mean_square_error(obs, model):
    return np.sqrt(np.mean((obs - model)**2))

def anomaly_correlation_coefficient(obs, model):
    obs_anomaly = obs - np.mean(obs)
    model_anomaly = model - np.mean(model)
    return np.corrcoef(obs_anomaly, model_anomaly)[0, 1]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/compute', methods=['POST'])
def compute_metrics():
    try:
        obs_data_file = request.files['obs_data']
        model_data_file = request.files['model_data']
        metrics = request.form.getlist('metrics')
        plot_type = request.form.get('plotType', None)

        if not obs_data_file or not model_data_file or not metrics:
            flash('Please upload both data files and select at least one metric.')
            return redirect(url_for('index'))

        obs_data_path = os.path.join(app.config['UPLOAD_FOLDER'], obs_data_file.filename)
        model_data_path = os.path.join(app.config['UPLOAD_FOLDER'], model_data_file.filename)

        obs_data_file.save(obs_data_path)
        model_data_file.save(model_data_path)

        obs_data = xr.open_dataarray(obs_data_path)
        model_data = xr.open_dataarray(model_data_path)

        if obs_data is None or model_data is None:
            flash('Error loading data files.')
            return redirect(url_for('index'))

        results = {}
        if 'MeanAbsoluteError' in metrics:
            results['MAE'] = mean_absolute_error(obs_data.values, model_data.values)
        if 'RootMeanSquareError' in metrics:
            results['RMSE'] = root_mean_square_error(obs_data.values, model_data.values)
        if 'AnomalyCorrelationCoefficient' in metrics:
            results['ACC'] = anomaly_correlation_coefficient(obs_data.values, model_data.values)

        if not results:
            flash('No results computed. Please check the input data and metrics.')
            return redirect(url_for('index'))

        return render_template('results.html', results=results)
    except KeyError as e:
        flash(f'Missing form field: {e}')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'An error occurred: {e}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
