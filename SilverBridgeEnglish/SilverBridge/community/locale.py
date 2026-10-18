"""English labels for legacy storage codes; existing databases remain compatible."""
LABELS = {'手机操作': 'Phone help', '视频通话': 'Video calls', '办事步骤': 'Everyday tasks', '其他问题': 'Other questions', '花生': 'Peanut', '坚果': 'Tree nuts', '蛋': 'Egg', '奶': 'Milk', '鱼': 'Fish', '大豆': 'Soy', '麸质': 'Gluten', '主食': 'Staple', '蛋白': 'Protein', '果蔬': 'Fruit & vegetables', '早': 'Breakfast', '午': 'Lunch', '晚': 'Dinner', '全部': 'All', '菜品': 'Dishes', '粥': 'Porridges', '汤': 'Soups', '饮品': 'Drinks', '羹': 'Thick soups & puddings', '干果': 'Nuts', '糕点': 'Cakes', '其它': 'Other', '想尝试': 'Would try', '已经做过': 'Made it', '不合口味': 'Not for me'}

def label(value):
    return LABELS.get(value, value)
