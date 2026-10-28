from unittest.mock import patch
import pytest
import streamlit as st
from pump.account import AccountError, action, sign_in


def test_login_rejects_email_and_never_builds_arbitrary_domain():
    with pytest.raises(AccountError), patch('pump.account.auth_request') as request:
        sign_in('admin@attacker.example', 'password')
    request.assert_not_called()


def test_api_uses_session_token_and_keeps_server_key_out_of_payload():
    st.session_state['sniper_session'] = {'access_token':'USER_TOKEN'}
    with patch('pump.account.config', return_value={'SUPABASE_URL':'https://example.supabase.co','SUPABASE_KEY':'SERVER_KEY'}), patch('pump.account.requests.post') as request:
        request.return_value.ok = True
        request.return_value.json.return_value = {'profile':{}}
        action('session')
        assert request.call_args.kwargs['headers']['Authorization']=='Bearer USER_TOKEN'
        assert 'SERVER_KEY' not in str(request.call_args)
