from django.db import migrations


def seed_awards(apps, schema_editor):
    Award = apps.get_model('memorial', 'Award')

    awards_data = [
        {
            'name': 'Medal of Honor (Army)',
            'short_description': 'The highest military decoration awarded by the United States government, presented to members of the Army for conspicuous gallantry and intrepidity at the risk of life above and beyond the call of duty.',
            'long_description': '''The Medal of Honor is the United States of America's highest and most prestigious personal military decoration that may be awarded to recognize U.S. military service members who have distinguished themselves by acts of valor.

The Army Medal of Honor was established by joint resolution of Congress on July 12, 1862. It is awarded to members of the United States Army who distinguish themselves through conspicuous gallantry and intrepidity at the risk of life above and beyond the call of duty while engaged in action against an enemy of the United States.

The medal is presented by the President of the United States in the name of Congress, which is why it is sometimes referred to as the "Congressional Medal of Honor."''',
            'image_filename': 'MoHArmy',
            'order': 1,
        },
        {
            'name': 'Medal of Honor (Navy)',
            'short_description': 'The highest military decoration awarded to members of the United States Navy and Marine Corps for valor in combat against an enemy force.',
            'long_description': '''The Navy Medal of Honor is presented to members of the United States Navy and Marine Corps who distinguish themselves through conspicuous gallantry and intrepidity at the risk of life above and beyond the call of duty.

The Navy variant of the Medal of Honor was established in 1861 and features a distinct design from the Army version. It depicts Minerva, the Roman goddess of wisdom and war, repulsing Discord.

Recipients must have distinguished themselves conspicuously by gallantry and intrepidity at the risk of their lives above and beyond the call of duty while engaged in action against an enemy of the United States.''',
            'image_filename': 'MoHNavy',
            'order': 2,
        },
        {
            'name': 'Medal of Honor (Air Force)',
            'short_description': 'The highest military decoration awarded to members of the United States Air Force for extraordinary heroism in combat.',
            'long_description': '''The Air Force Medal of Honor is the highest military decoration that may be awarded to a member of the United States Air Force. It was established in 1965 after the Air Force created its own distinctive version of the medal.

The design features the head of the Statue of Liberty surrounded by a wreath. Recipients must have distinguished themselves conspicuously by gallantry and intrepidity at the risk of life above and beyond the call of duty while engaged in military operations involving conflict with an opposing foreign force.

Prior to 1965, Air Force personnel received the Army Medal of Honor.''',
            'image_filename': 'MoHAirForce',
            'order': 3,
        },
        {
            'name': 'Distinguished Service Cross',
            'short_description': 'The second highest military decoration that can be awarded to a member of the United States Army, for extraordinary heroism in combat.',
            'long_description': '''The Distinguished Service Cross is the second highest military decoration that can be awarded to a member of the United States Army, ranking immediately below the Medal of Honor.

The medal is awarded to soldiers who distinguish themselves by extraordinary heroism not justifying the Medal of Honor. The act or acts of heroism must have been so notable and involved risk of life so extraordinary as to set the individual apart from their comrades.

Established by Congress on July 9, 1918, the Distinguished Service Cross has been awarded to soldiers who have displayed extraordinary heroism in combat with an armed enemy force.''',
            'image_filename': 'DistinguishedServiceCross',
            'order': 4,
        },
        {
            'name': 'Navy Cross',
            'short_description': 'The second highest military decoration that may be awarded to a member of the United States Navy or Marine Corps, for extraordinary heroism in combat.',
            'long_description': '''The Navy Cross is the second highest military decoration that may be awarded to a member of the United States Navy, Marine Corps, or Coast Guard. It is awarded for extraordinary heroism in combat.

Established by Act of Congress on February 4, 1919, the Navy Cross ranks immediately below the Medal of Honor and above the Silver Star. The Navy Cross may be awarded to any person who, while serving with the Navy or Marine Corps, distinguishes themselves by extraordinary heroism not justifying the Medal of Honor.

The heroic act must take place while engaged in action against an enemy of the United States, in military operations involving conflict with an opposing foreign force, or while serving with friendly foreign forces engaged in an armed conflict against an opposing armed force.''',
            'image_filename': 'NavyCross',
            'order': 5,
        },
        {
            'name': 'Air Force Cross',
            'short_description': 'The second highest military decoration that can be awarded to a member of the United States Air Force, for extraordinary heroism in combat.',
            'long_description': '''The Air Force Cross is the second highest military decoration that can be awarded to a member of the United States Air Force and Space Force. It is equivalent to the Army's Distinguished Service Cross and the Navy Cross.

Established on July 6, 1960, the Air Force Cross is awarded for extraordinary heroism while engaged in action against an enemy of the United States, or while engaged in military operations involving conflict with an opposing foreign force.

The act or acts of heroism must be so notable and involve risk of life so extraordinary as to set the individual apart from their comrades, but not to the degree required for the Medal of Honor.''',
            'image_filename': 'AirForceCross',
            'order': 6,
        },
        {
            'name': 'Silver Star',
            'short_description': 'The third highest military combat decoration that can be awarded to a member of the United States Armed Forces, for gallantry in action.',
            'long_description': '''The Silver Star is the third highest military combat decoration that can be awarded to a member of any branch of the United States Armed Forces for gallantry in action against an enemy of the United States.

Originally established as the Citation Star on July 9, 1918, the medal was redesignated as the Silver Star on August 8, 1932. It is awarded for gallantry in action that does not warrant a Medal of Honor, Distinguished Service Cross, Navy Cross, or Air Force Cross.

The Silver Star may be awarded to any person who, while serving in any capacity with the Armed Forces, distinguishes themselves by gallantry in action against an enemy of the United States.''',
            'image_filename': 'SilverStar.png',
            'order': 7,
        },
        {
            'name': 'Croix de Guerre',
            'short_description': 'A French military decoration honoring individuals who distinguished themselves by acts of heroism involving combat with the enemy.',
            'long_description': '''The Croix de Guerre (Cross of War) is a French military decoration, first created in 1915 to recognize acts of heroism involving combat with enemy forces.

Multiple versions have been issued, including those from World War I (1914-1918), World War II (1939-1945), and the Theatre of External Operations. The decoration was awarded to both French and Allied soldiers, including many American service members.

The Croix de Guerre is awarded to individuals who have been mentioned in dispatches for acts of heroism involving combat with the enemy. American recipients often received the decoration for actions during both World Wars and subsequent conflicts.''',
            'image_filename': 'CroixDeGuerre',
            'order': 8,
        },
        {
            'name': 'Médaille Militaire',
            'short_description': 'The third highest French military decoration, awarded to enlisted personnel and non-commissioned officers for acts of bravery.',
            'long_description': '''The Médaille Militaire is the third highest French military decoration after the Légion d'honneur and the Ordre de la Libération. It was established in 1852 by Louis-Napoléon Bonaparte.

Unlike the Légion d'honneur, the Médaille Militaire is awarded exclusively to enlisted personnel and non-commissioned officers for acts of bravery in combat, or to generals who have commanded in chief in the face of the enemy.

Many American service members received this prestigious decoration during World War I and World War II for their gallantry while serving alongside French forces.''',
            'image_filename': 'MedailleMilitaire',
            'order': 9,
        },
        {
            'name': 'Victoria Cross',
            'short_description': 'The highest military decoration awarded for valor "in the presence of the enemy" to members of the British and Commonwealth armed forces.',
            'long_description': '''The Victoria Cross is the highest military decoration awarded for valor "in the presence of the enemy" to members of the British and Commonwealth armed forces. It was introduced on January 29, 1856 by Queen Victoria.

The Victoria Cross takes precedence over all other orders, decorations, and medals. It is awarded for "most conspicuous bravery, or some daring or pre-eminent act of valour or self-sacrifice, or extreme devotion to duty in the presence of the enemy."

While primarily awarded to British and Commonwealth personnel, some American service members who served with Commonwealth forces have received this prestigious decoration.''',
            'image_filename': 'VictoriaCross',
            'order': 10,
        },
        {
            'name': 'Distinguished Service Order',
            'short_description': 'A British military decoration awarded for meritorious or distinguished service by officers of the armed forces during wartime.',
            'long_description': '''The Distinguished Service Order (DSO) is a British military decoration awarded for meritorious or distinguished service by officers of the armed forces during wartime, typically in combat situations.

Established on September 6, 1886 by Queen Victoria, the DSO is typically awarded to officers ranked Major or higher, though it can be awarded to junior officers for acts of leadership under fire.

The DSO has been awarded to American officers serving with British and Commonwealth forces, particularly during World War I and World War II, recognizing their exceptional leadership and service.''',
            'image_filename': 'DistinguishedServiceOrder.png',
            'order': 11,
        },
    ]

    for award_data in awards_data:
        Award.objects.create(**award_data)


def remove_awards(apps, schema_editor):
    Award = apps.get_model('memorial', 'Award')
    Award.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("memorial", "0007_award_personaward"),
    ]

    operations = [
        migrations.RunPython(seed_awards, remove_awards),
    ]
