def run_bounded_diagnosis(self):
    s = self.subject
    s.fixture.contract['integrations'] = {'nk': 'DISABLED', 'critics': 'ENABLED'}
    s.contract.write_text(json.dumps(s.fixture.contract, ensure_ascii=False), encoding='utf-8')
    resource_config = json.loads(s.fees.config.read_bytes())
    resource_config['provider']['max_in_flight'] = 1
    s.fees.config.write_bytes(json.dumps(resource_config, ensure_ascii=False).encode('utf-8'))
    terms = s.full_terms()
    terms['expires_at'] = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    for hook in ('critics_plot', 'critics_text'):
        terms['stages'].append(hook)
        terms['roles'][hook] = [hook]
    s.sign(terms=terms)
    s.create()
    with cost_guard.accounting.locked_ledger():
        pass
    outputs = s.fixture._outputs()
    s.fixture.rereview_messages = []
    cnw_calls, native_calls, service_calls = ([], [], [])

    def cnw_transport(run, *, url, body, request_id):
        stage = request_id.removeprefix('cnw-' + s.run_id + '-').rsplit('-', 1)[0]
        role, extra = (None, None)
        if stage in {'multi_lens_review', 're_review', 'adversarial_verify'}:
            packet = json.loads(body['messages'][1]['content'])
            role = packet.get('lens_id') or packet.get('verifier_id')
            if 'finding_id' in packet:
                extra = {'finding_id': packet['finding_id']}
        if stage == 'refine':
            self.assertIn('MOCK_ONLY selected native expression', json.dumps(body['messages']))
        content = s.fixture._response(stage, role, extra, outputs, body['messages'])
        cnw_calls.append({'stage': stage, 'role': role, 'messages': body['messages']})
        return SimpleNamespace(status_code=200, json=lambda: {'id': 'SIMULATED-' + request_id, 'model': r.MODEL, 'choices': [{'finish_reason': 'stop', 'message': {'content': content}}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 10}})
    replies = ['Expert 1\nStructure persona\nExpert 2\nEnding persona\nExpert 3\nOriginal persona\nLeader\nLeader persona', 'Question: Is the repair visible?\nWhy: MOCK_ONLY structure.', 'Question: Is the offer earned?\nWhy: MOCK_ONLY ending.', 'Question: Does the neighbor choose?\nWhy: MOCK_ONLY original.', 'Question: Is the offer earned?\nWhy: MOCK_ONLY selection.', 'MOCK_ONLY native imagery alternative', 'MOCK_ONLY native voice alternative', 'MOCK_ONLY selected native expression']

    def native_http(client, request, *args, **kwargs):
        self.assertEqual(request.url.host, 'api.deepseek.com')
        body = json.loads(request.read())
        self.assertEqual(body['model'], r.MODEL)
        number = len(native_calls)
        if number >= len(replies):
            raise AssertionError('unexpected native retry')
        native_calls.append({'request': body, 'simulation_status': 'SIMULATED'})
        return httpx.Response(200, request=request, json={'id': 'SIMULATED-NATIVE-' + str(number), 'model': r.MODEL, 'object': 'chat.completion', 'created': 0, 'simulation_status': 'SIMULATED', 'fixture_only': True, 'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': replies[number]}}], 'usage': {'prompt_tokens': 12, 'completion_tokens': 8, 'total_tokens': 20}})
    real_run = subprocess.run

    def service(command, **kwargs):
        if len(command) < 2 or Path(str(command[1])) != r.ROOT / 'tools/p2_06_critics_run.py':
            return real_run(command, **kwargs)
        service_calls.append(list(command))
        previous = Path.cwd()
        try:
            result = native.main(command[2:])
            mark('native_service_finished')
        finally:
            os.chdir(previous)
        return subprocess.CompletedProcess(command, result, stdout='', stderr='')
    with _isolated_live_transport(s.fixture.temp, data_home=s.fixture.data_home, projects=[s.root], runs=[s.run], transport=cnw_transport), patch('subprocess.run', side_effect=service), patch.object(httpx.Client, 'send', native_http):
        for stage in r.CNW_STAGES[:6]:
            recovery.execute_checked(s.run, stage)
        mark('before_one_lens')
        candidates = cnw_request_identity.expected_requests(s.run, stage='multi_lens_review', role_id='style')
        requests = [call for call in candidates if call['stage'] == 'multi_lens_review' and call['role_id'] == 'style']
        if len(requests) != 1:
            raise RuntimeError('DIAGNOSTIC_EXPECTED_ONE_LEGITIMATE_LENS')
        r._parallel_provider_calls(s.run, requests)
        mark('after_one_lens')
