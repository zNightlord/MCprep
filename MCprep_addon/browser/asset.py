 
Skip to main content
Developer Forum
Chat
User Community
Ideas
Report a Bug
profile, messages, bookmarks and preferences2
Do you want to install Developer Forum on this device?​
This is a forum for Blender development. For questions about using blender, feature requests and bugs, please use the links above.
Implementing custom drag operator with template_asset_view
Archive
Python API

Andrew_Peel
Dec '21
I have been working on porting over my home builder add-on to work with Blender 3.0. I have determined that it would be best to implement the library browsing using the template_asset_view() interface.

I have implemented the ability to use a custom operator when dragging an asset from the view. I am trying to raycast from the mouse location and need access to the 3D view region data, but context.region_data returns None. Even though the operator is being called in the 3D viewport the asset browser is changing context.

I have tried manually getting the region data by looping through the areas and pass in the correct 3d space data, but the view matrix is incorrect. It seems like it is the view matrix from the sidebar. I can run the operator from the search command and it works just fine.

Here is a link to a simple test add-on with the issue. I’m not sure if I should report this as a bug or if there is something I am missing.

drive.google.com
test_asset_library.zip 19
Google Drive file.






created
Dec '21
last reply
Dec '21
8
replies

julianeisel
Dec '21
Basic issue is that you don’t get the needed context in the modal operator. We could allow giving the template the operator context somehow (so you can pass INVOKE_REGION_WIN for example), and maybe we should do that. I’m just a bit wary of extending the already enormous template argument list even further. Hopefully the template can follow a better design before too long.

Meanwhile, just explicitly looking up and using the main region should do the trick: ✎ P2649 (An Untitled Masterwork) 10

1





Andrew_Peel

Dec '21
Thanks for the reply. I tried to implement the changes and I don’t receive an error, but the ray cast doesn’t return the correct results. The get_selection_point function is always returning (0,0,0) even if my cursor is directly on a mesh. If I move my cursor around in the sidebar i can get it to trigger a hit, so it’s like the view_matrix is the related to the sidebar not the 3D viewport. Is there anything that I might have setup wrong?






cconst
Dec '21
I tried various hacks in order to make it work, though is mostly based on experience and pure luck, I was just about to abandon this effort. :slight_smile:

get_selection_point is a straight copy from the template code, I didn’t double checked it at all.

The id name bl_idname = "object.test_asset_library_place_object" is changed to object just to make it sure that the operator will run on the OBJECT context. Though perhaps you would possibly introduce your own operator namespace as originally you intended, though you will have to create a poll method and lock the operator on the OBJECT context mode again. My estimation on this is that the operator can either be invoked from the panel context or the object context but at least you will have to discard the panel context for good, once you leave the panel area you enter the view3D area and then the operator is invoked on the OBJECT context (thus you get the region_data for 3D region). But either way if you consider that it does not worth the trouble of trying it just stick to OBJECT context for good.

While on the panel, when the operator is invoked drag_operator="object.test_asset_library_place_object('INVOKE_DEFAULT')", the INVOKE_DEFAULT parameter can be thrown as well, is a common idiom used often. In this case you will be able to override completely the context from where it operator is invoked (the sidepanel) and thus the modal operator will use it’s own predefined one (as in bl_idname).

P.S. If any of my interpretations are wrong or anyone has some comments on them, can mention anything needed for better clarification.








Andrew_Peel

Dec '21
Thanks for looking into this, but it’s still not working on my side. It appears to work, but it is just using the built in drag and drop object functionality. I assume this is happening because it doesn’t recognize the bl_idname of the operator with ‘INVOKE_DEFAULT’. This works when placing the operator on a regular panel, but not when it is assigned to the drag_operator of the template_asset_view control.

Hopefully @julianeisel or one of the other Blender developers can help us out. Implementing a custom drop operator is very close, but without access to the 3d view matrix it limits what is possible.

If you come across anyway around this let me know. This is the only road block I am running into that is not allowing me to continue to port over home builder to Blender 3.0.






cconst

Dec '21
I have tested this code in Blender 3.0 by the way, it worked nicely for me although I have not tested it extensively in all situations, it seems good so far.

I have no idea about prior versions though, are you running on 2.9 LTS?






Andrew_Peel

Dec '21
Yeah you are able to drag and drop an item from the library, but what I am trying to do is implement a custom drag and drop operator. This will allow me to logically snap assets together. For example when you drag a door onto a wall it automatically adds a boolean to cut a hole in the wall.

Right now the drag and drop event you are using is the built in one from Blender, and you cannot define custom logic how assets should be placed. If you remove the drag_operator parameter from layout.template_asset_view() you will get the same results.

Let me know if I am missing something, but I am pretty sure the code you posted is not using the object.test_asset_library_place_object operator when the asset is dragged from the library…

1





julianeisel
Dec '21
Just managed to look into this again, and the error is actually quite simple to fix. Issue was usage of event.mouse_region_x/y which is the coordinate relative to the active region, which is of course not the region the script is operating in.

Full patch:

diff --git a/old/__init__.py b/new/__init__.py
index c54270a..b9dd5b3 100644
--- a/old/__init__.py
+++ b/new/__init__.py
@@ -46,14 +46,12 @@ def load_library(dummy):
     for workspace in bpy.data.workspaces:
         workspace.asset_library_ref = LIBRARY_NAME
 
-def get_selection_point(context, event):
+def get_selection_point(context, region, event):
     """Run this function on left mouse, execute the ray cast"""
     # get the context arguments
     scene = context.scene
-    region = context.region
-    #NO 3D VIEW REGION DATA FOUND???
-    rv3d = context.region_data
-    coord = event.mouse_region_x, event.mouse_region_y
+    rv3d = region.data
+    coord = event.mouse_x - region.x, event.mouse_y - region.y
 
     # get the ray from the viewport and mouse
     view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
@@ -135,10 +133,21 @@ class test_library_OT_place_object(bpy.types.Operator):
             self.obj = obj        
             context.view_layer.active_layer_collection.collection.objects.link(obj)  
 
+    @staticmethod
+    def get_main_region(context):
+        for region in context.area.regions:
+            if region.type == 'WINDOW':
+                return region
+        return None
+
     def modal(self, context, event):
         context.view_layer.update()
 
-        selected_point, selected_obj, selected_normal = get_selection_point(context,event)
+        region = self.get_main_region(context)
+        if not region:
+            return {'RUNNING_MODAL'}
+
+        selected_point, selected_obj, selected_normal = get_selection_point(context,region,event)
         self.obj.location = selected_point
 
         if event.type == 'LEFTMOUSE' and event.value == 'PRESS':

1





Andrew_Peel

Dec '21
Thanks Julian! That works just like I would expect. I didn’t think to look into the get_selection_point function since this was taken right from one of the python templates, but it makes sense since we have to pass in the correct region. I’m back to working on migrating home builder to 3.0.






Reply
You will see a count of new replies because you read this topic.
Suggested Topics

Real-time Compositor: Feedback and discussion 13
Feature & Design Feedback
user-feedback
compositor
22h

Remove legacy instancing 42
Feature & Design Feedback
modeling
geometry-nodes
modifiers
1d

Geometry Nodes 69
User Feedback
6d

Cycles AMD HIP device feedback 101
Feature & Design Feedback
rendering
7d

Paint Mode: Design Discussion & Feedback 79
Feature & Design Feedback
Mar 23
There are 11 unread and 11 new topics remaining, or browse other topics in 
Python API

Quote