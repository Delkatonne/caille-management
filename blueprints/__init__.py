"""blueprints — un blueprint par grand bloc fonctionnel de la ferme."""


def register_blueprints(app):
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .production import bp as production_bp
    from .stocks import bp as stocks_bp
    from .finances import bp as finances_bp
    from .personnel import bp as personnel_bp

    for bp in (auth_bp, dashboard_bp, production_bp, stocks_bp, finances_bp, personnel_bp):
        app.register_blueprint(bp)
