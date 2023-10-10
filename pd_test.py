from pypushdeer import PushDeer

pushdeer = PushDeer(pushkey="PDU20739T7ZemNBLmqiMV8CYNKUm665tYsoAshLKo")
pushdeer.send_text("hello world", desp="optional description")
# pushdeer.send_markdown("test", desp="this is a test PushDeer")
