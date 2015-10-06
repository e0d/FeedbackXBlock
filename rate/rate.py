# coding: utf-8
"""
This is an XBlock designed to allow people to provide feedback on our
course resources.
"""

import random

import pkg_resources

from xblock.core import XBlock
from xblock.fields import Scope, Integer, String, List, Float
from xblock.fragment import Fragment

try:
    from eventtracking import tracker
except ImportError:
    class tracker(object):  # pylint: disable=invalid-name
        """
        Define tracker if eventtracking cannot be imported. This is a workaround
        so that the code works in both edx-platform and XBlock workbench (the latter
        of which does not support event emission). This should be replaced with XBlock's
        emit(), but at present, emit() is broken.
        """
        def __init__(self):
            """ Do nothing """
            pass

        @staticmethod
        def emit(param1, param2):
            """ In workbench, do nothing for event emission """
            pass

class RateXBlock(XBlock):
    """
    This is an XBlock -- eventually, hopefully an aside -- which
    allows you to rate content in the course. We've wanted this for a
    long time, but Dartmouth finally encourage me to start to build
    this.
    """

    default_prompt = {'string':"Please provide us feedback on this section.",
                      'likert':"Please rate your overall experience with this section.",
                      'mouseovers':["Excellent", "Good", "Average", "Fair", "Poor"],
                      'icons':[u"😁",u"😊",u"😐",u"☹",u"😟"]}
    
    prompts = List(
        default=[default_prompt,
                 {'string':"What could be improved to make this section more clear?",
                  'likert':"Was this section clear or confusing?."}], 
        scope=Scope.settings,
        help="Freeform user prompt",
        xml_node = True
    )

    prompt_choice = Integer(
        default=-1, scope=Scope.user_state,
        help="Random number generated for p. -1 if uninitialized"
    )

    
    user_vote = Integer(
        default=-1, scope=Scope.user_state,
        help="How user voted. -1 if didn't vote"
    )

    p = Float(
        default=100, scope=Scope.settings,
        help="What percent of the time should this show?"
    )

    p_r = Float(
        default=-1, scope=Scope.user_state,
        help="Random number generated for p. -1 if uninitialized"
    )

    
    vote_aggregate = List(
        default=None, scope=Scope.user_state_summary,
        help="A list of user votes"
    )

    user_feedback = String(default = "", scope=Scope.user_state,
                        help = "Feedback")

    def resource_string(self, path):
        """Handy helper for getting resources from our kit."""
        data = pkg_resources.resource_string(__name__, path)
        return data.decode("utf8")

    def student_view(self, context=None):
        """
        The primary view of the RateXBlock, shown to students
        when viewing courses.
        """

        # Figure out which prompt we show. We set self.prompt_choice to
        # the index of the prompt. We set it if it is out of range (either
        # uninitiailized, or incorrect due to changing list length). Then,
        # we grab the prompt, prepopulated with defaults.
        if self.prompt_choice < 0 or self.prompt_choice >= len(self.prompts):
            self.prompt_choice = random.randint(0, len(self.prompts)-1)        
        prompt = dict(self.default_prompt)
        prompt.update(self.prompts[self.prompt_choice])

        # Now, we render the RateXBlock. This may be redundant, since we
        # don't always show it.
        html = self.resource_string("static/html/rate.html")
        scale_item = u'<input id="radio_{i}" type="radio" name="rate_scale" class="rate_radio" title="{level}" {active}><label for="radio_{i}" title="{level}">{icon}<span class="rate_sr_text">{level}</span></label></input>'
        indexes = range(len(prompt['icons']))
        active_vote = ["checked" if i == self.user_vote else "" for i in indexes]
        scale = u"".join(scale_item.format(level=level, icon=icon, i=i, active=active) for (level,icon,i,active) in zip(prompt['mouseovers'], prompt['icons'], indexes, active_vote))
        rendered = html.format(self=self, scale=scale, string_prompt = prompt['string'], likert_prompt = prompt['likert'])

        # We initialize self.p_r if not initialized -- this sets whether
        # or not we show it. From there, if it is less than odds of showing,
        # we set the fragment to the rendered XBlock. Otherwise, we return
        # empty HTML. There ought to be a way to return None, but XBlocks
        # doesn't support that. 
        if self.p_r == -1:
            self.p_r = random.uniform(0, 100)
        if self.p_r < self.p:
            frag = Fragment(rendered)
        else:
            frag = Fragment(u"")

        # Finally, we do the standard JS+CSS boilerplate. Honestly, XBlocks
        # ought to have a sane default here.
        frag.add_css(self.resource_string("static/css/rate.css"))
        frag.add_javascript(self.resource_string("static/js/src/rate.js"))
        frag.initialize_js('RateXBlock')
        return frag

    @XBlock.json_handler
    def vote(self, data, suffix=''):
        """
        Handle voting
        """
        # Make sure we're initialized
        if not self.vote_aggregate:
            self.vote_aggregate = [0]*len(prompt['mouseovers'])

        # Remove old vote if we voted before
        if self.user_vote != -1:
            self.vote_aggregate[self.user_vote] -= 1

        tracker.emit('edx.ratexblock.likert_rate', 
                     {'old_vote' : self.user_vote,
                      'new_vote' : data['vote']})

        self.user_vote = data['vote']
        self.vote_aggregate[self.user_vote] += 1
        return {"success": True}

    @XBlock.json_handler
    def feedback(self, data, suffix=''):
         
        tracker.emit('edx.ratexblock.string_feedback', 
                     {'old_feedback' : self.user_feedback, 
                      'new_feedback' : data['feedback']})
        self.user_feedback = data['feedback']

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("RateXBlock",
             """<vertical_demo>
                <rate p="50"/>
                <rate p="50"/>
                <rate p="50"/>
                </vertical_demo>
             """),
        ]
