import java.util.Map;
import java.util.Set;

public final class SentinelAuthorizationLesson {
    enum Actor { DISCOVERY_APP, BUSINESS_APP, SENTINEL_CONTROL, REPLICATION }
    enum Action { DISCOVER_PRIMARY, READ_BUSINESS, WRITE_BUSINESS,
                  CHANGE_ROLE, CONFIGURE_REPLICA, RECEIVE_REPLICATION }

    static final Map<Actor, Set<Action>> POLICY = Map.of(
            Actor.DISCOVERY_APP, Set.of(Action.DISCOVER_PRIMARY),
            Actor.BUSINESS_APP, Set.of(Action.READ_BUSINESS, Action.WRITE_BUSINESS),
            Actor.SENTINEL_CONTROL, Set.of(Action.CHANGE_ROLE, Action.CONFIGURE_REPLICA),
            Actor.REPLICATION, Set.of(Action.RECEIVE_REPLICATION));

    static boolean permits(Actor actor, Action action) {
        return POLICY.getOrDefault(actor, Set.of()).contains(action);
    }

    static void expect(boolean expected, Actor actor, Action action) {
        if (permits(actor, action) != expected) {
            throw new AssertionError(actor + " / " + action);
        }
    }

    public static void main(String[] args) {
        expect(true, Actor.DISCOVERY_APP, Action.DISCOVER_PRIMARY);
        expect(false, Actor.DISCOVERY_APP, Action.CHANGE_ROLE);
        expect(true, Actor.BUSINESS_APP, Action.WRITE_BUSINESS);
        expect(false, Actor.BUSINESS_APP, Action.CONFIGURE_REPLICA);
        expect(true, Actor.SENTINEL_CONTROL, Action.CHANGE_ROLE);
        expect(false, Actor.REPLICATION, Action.WRITE_BUSINESS);
        System.out.println("3 required permissions and 3 required denials checked");
    }
}
