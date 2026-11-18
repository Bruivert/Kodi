from resources.lib import fondo


def test_worker_runs_every_job_until_kodi_closes_and_survives_errors():
    calls, logs, waits = [], [], iter([False, False, True])

    def renew():
        calls.append('renew')
        return 'peliculas.estrenos'

    def broken():
        calls.append('broken')
        raise IOError('sin red')
    worker = fondo.Worker([('fila', renew), ('fondos', broken)], lambda seconds: next(waits), logs.append)
    worker.run()  # en el servicio corre en su propio hilo; aquí se llama directamente
    assert calls == ['renew', 'broken', 'renew', 'broken']
    assert logs.count('fila: peliculas.estrenos') == 2 and logs.count('fondos: sin red') == 2
    assert worker.daemon  # no impide que Kodi se cierre
