import java.lang.reflect.*;
import java.util.*;
public class InspectAnimation {
 static Object call(Object o,String n,Object... args)throws Exception {
  for(Method m:o.getClass().getMethods()) if(m.getName().equals(n)&&m.getParameterCount()==args.length) return m.invoke(o,args);
  throw new Exception(n);
 }
 public static void main(String[] args)throws Exception {
  Class.forName("zombie.core.skinnedmodel.model.jassimp.JAssImpImporter").getMethod("Init").invoke(null);
  Class<?> j=Class.forName("jassimp.Jassimp");
  for(String path:args){
   System.out.println(path);
   Object scene;
   try {scene=j.getMethod("importFile",String.class).invoke(null,path);}
   catch(InvocationTargetException e){String s=e.getCause().toString();throw new Exception(s.substring(0,Math.min(180,s.length())));}
   if(((List<?>)call(scene,"getAnimations")).isEmpty())throw new Exception("No animations imported");
   for(Object a:(List<?>)call(scene,"getAnimations")) {
    System.out.println("clip="+call(a,"getName")+" duration="+call(a,"getDuration")+" fps="+call(a,"getTicksPerSecond")+" channels="+call(a,"getNumChannels"));
    if((int)call(a,"getNumChannels")<40 || (double)call(a,"getDuration")<=0)throw new Exception("Incomplete skeleton or empty clip");
    boolean animated=false;
    for(Object c:(List<?>)call(a,"getChannels")) {
     String name=(String)call(c,"getNodeName");
     int n=(int)call(c,"getNumRotKeys");
     for(String component:List.of("W","X","Y","Z"))for(int k=0;k<n;k++) {
      float value=(float)call(c,"getRotKey"+component,k);
      if(!Float.isFinite(value))throw new Exception("Invalid rotation: "+name);
      if(Math.abs(value-(float)call(c,"getRotKey"+component,0))>.02f)animated=true;
     }
     int positions=(int)call(c,"getNumPosKeys");
     if(positions==0 || n==0)throw new Exception("Missing transform track: "+name);
     for(String component:List.of("X","Y","Z"))for(int k=0;k<positions;k++)
      if(!Float.isFinite((float)call(c,"getPosKey"+component,k)))throw new Exception("Invalid position: "+name);
    }
    if(!animated)throw new Exception("Clip contains no movement");
   }
  }
 }
}
