"""Compact presentation helpers. Collection and screening rules are unchanged."""
import html
import streamlit as st

CSS = '''<style>
.dex-workspace-head{margin:0 0 5px}.dex-workspace-head h1{font-size:30px!important;line-height:1.2!important;letter-spacing:-1px;margin:0!important;padding:0!important;color:#f0f5f8}.dex-workspace-head p{font-size:13px;color:#899ba9;margin:8px 0 0}
.dex-run-line{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;padding:12px 0 16px;color:#8f9fae;font-size:12px}.dex-run-line>span{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.dex-health{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:600;color:#9be3c6;background:#16392c66;border:1px solid #2a5c4766;padding:5px 10px;border-radius:20px}.dex-health i{width:6px;height:6px;border-radius:100%;background:currentColor}.dex-health.partial{color:#ebc985;border-color:#79603266;background:#5c461e33}.dex-health.error{color:#f2a7b5;border-color:#8e425566;background:#55243344}.dex-health.pending{color:#b0bdca;border-color:#42546477;background:#29364144}
[class*="st-key-dex_summary_"]{border:1px solid #263440!important;border-radius:12px!important;background:linear-gradient(130deg,#141d25,#111820);padding:15px 18px!important}
[class*="st-key-dex_summary_"] [data-testid="stMetricLabel"]{color:#92a5b4;font-size:12px}[class*="st-key-dex_summary_"] [data-testid="stMetricValue"]{font-size:29px;font-weight:650;letter-spacing:-.7px}
@media(max-width:700px){.dex-workspace-head h1{font-size:25px!important}.dex-run-line{padding-top:4px;gap:8px}}
</style>'''


def health(run, now, demo=False):
    latest=run.get('completed_at') or run.get('started_at') or 0
    issues=run.get('source_errors') or []
    if demo:
        return 'Demonstração','pending'
    if run.get('status')=='error':
        return 'Coleta interrompida','error'
    if not latest:
        return 'Aguardando coleta','pending'
    if now-latest>max(180,run.get('rules',{}).get('interval_seconds',60)*3):
        return 'Dados desatualizados','error'
    if run.get('status')=='running':
        return 'Atualizando','pending'
    if issues or run.get('status')=='partial':
        return 'Dados parciais','partial'
    return 'Atualizado','ok'


def status_line(run, now, stamp, demo=False, mode=None):
    label,tone=health(run,now,demo)
    latest=run.get('completed_at') or run.get('started_at')
    interval=run.get('rules',{}).get('interval_seconds',60)
    meta='Dados simulados' if demo else 'Última coleta '+stamp(latest)+' · Brasília'
    detail=mode or f'Coleta a cada {interval}s · Triagem parcial'
    if not demo and run.get('checked') is not None:
        detail+=f" · {run['checked']} consultados no ciclo"
    st.markdown(f'<div class="dex-run-line"><span><b class="dex-health {tone}" title="Detalhes em Critérios e operação"><i></i>{html.escape(label)}</b><span>{html.escape(detail)}</span></span><span>{html.escape(meta)}</span></div>',unsafe_allow_html=True)
    if tone=='error':
        st.warning('A coleta falhou ou está sem atualização recente. Confira a operação antes de usar os dados.')


def operation_details(run, stamp):
    st.caption('Atualização da tela: 15s · Coleta prevista: 1 min · Horários de Brasília')
    if run.get('completed_at') and run.get('started_at'):
        st.caption(f"Última coleta: {stamp(run['completed_at'])} · Duração: {max(0,run['completed_at']-run['started_at']):.1f}s · Consultadas: {run.get('checked',0)} · Falhas: {run.get('errors',0)}")
    issues=run.get('source_errors') or []
    if not issues:
        st.caption('Nenhuma ocorrência reportada no último ciclo.')
    for issue in issues:
        st.write('• '+str(issue))
