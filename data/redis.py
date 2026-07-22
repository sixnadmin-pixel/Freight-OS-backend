import redis

r = redis.Redis(
    host='silk-game-notable-14940.db.redis.io',
    port=16276,
    decode_responses=True,
    username="default",
    password="FjVtKnPw0QRG6h2GRt9puTs1WUaAyXfz",
)

# success = r.set('foo', 'bar')
# # True

# result = r.get('foo')
# print(result)
# # >>> bar

