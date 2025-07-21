from scheduler import LinkScheduler


def test_scheduler_busy_check():
    sent = []
    busy = True

    def send_fn(data):
        sent.append(data)

    def check():
        return busy

    sched = LinkScheduler(send_fn, window=0, busy_check=check)
    sched.queue_packet(b"hi", priority=5)
    sched.run_once()
    assert not sent
    busy = False
    sched.run_once()
    assert sent == [b"hi"]
