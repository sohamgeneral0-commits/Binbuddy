@app.route('/admin-dashboard.html')
def admin_dashboard():
    return render_template('admin-dashboard.html')

@app.route('/citizen-dashboard.html')
def citizen_dashboard():
    return render_template('citizen-dashboard.html')

@app.route('/worker-dashboard.html')
def worker_dashboard():
    return render_template('worker-dashboard.html')

@app.route('/municipal-dashboard.html')
def municipal_dashboard():
    return render_template('municipal-dashboard.html')

const routeMap = {
  'citizen':           'citizen-dashboard.html',
  'collector':         'worker-dashboard.html',
  'admin':             'admin-dashboard.html',
  'municipal_office':  'municipal-dashboard.html'
};
window.location.href = routeMap[data.user.role] || 'dashboard.html';