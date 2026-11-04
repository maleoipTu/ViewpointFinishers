import java.nio.file.*;

// Runs our behavioral tests with the exact Lua VM shipped by the installed game.
public class LuaCheck {
    public static void main(String[] args) throws Exception {
        var platformClass = Class.forName("se.krka.kahlua.j2se.J2SEPlatform");
        var tableClass = Class.forName("se.krka.kahlua.vm.KahluaTable");
        var threadClass = Class.forName("se.krka.kahlua.vm.KahluaThread");
        var platform = platformClass.getMethod("getInstance").invoke(null);
        var env = platformClass.getMethod("newEnvironment").invoke(platform);
        var thread = threadClass.getConstructor(Class.forName("se.krka.kahlua.vm.Platform"),tableClass).newInstance(platform,env);
        threadClass.getField("debugOwnerThread").set(thread,Thread.currentThread());
        var load = Class.forName("se.krka.kahlua.luaj.compiler.LuaCompiler").getMethod("loadstring",String.class,String.class,tableClass);
        for (String arg : args) {
            var file = Path.of(arg);
            var closure = load.invoke(null,Files.readString(file),file.toString(),env);
            var result = (Object[]) threadClass.getMethod("pcall",Object.class,Object[].class).invoke(thread,closure,new Object[0]);
            if (!Boolean.TRUE.equals(result[0])) {
                throw new RuntimeException(file+": "+java.util.Arrays.toString(result));
            }
            System.out.println("PASS "+file);
        }
    }
}
